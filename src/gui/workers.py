"""Background worker threads and shared GUI helpers for the main window.

Extracted from main_window.py so each worker can be reasoned about in
isolation, and so the file size of main_window.py stays manageable.

Contents:
- AnimatedProgressDialog — reusable indeterminate↔determinate progress dialog
- FileLoaderWorker        — loads sources, builds StringEntry list, sort keys
- StartupSyncWorker       — refreshes URL-backed sources on startup
- EnhancementsGeneratorWorker — runs scripts/generate_enhancements_ini.py
- P4kExtractWorker        — unp4k extraction of global.ini
- DataForgeExtractWorker  — unp4k + unforge + patch pipeline
- SelectAllDelegate       — Custom Value cell delegate (auto-select, EM3/EM4 wrap)
"""

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QProgressBar, QProgressDialog, QStyledItemDelegate

from src.parser.ini_parser import load_source_files, load_sources_from_settings
from src.utils.resource_path import resolve_patches_dir
from src.utils.settings import AppSettings
from src.utils.dataforge_diff import dirty_categories
logger = logging.getLogger(__name__)


class AnimatedProgressDialog(QProgressDialog):
    """Reusable progress dialog that toggles between indeterminate and determinate.

    Starts indeterminate (range 0-0, auto-animating). Call `set_progress(completed,
    total, message)` to switch to determinate; pass total=0 to drop back to
    indeterminate for phases with an unknown extent. The phase message shows
    in the label above the bar. In determinate mode the bar displays the
    percent-complete (default Qt ``%p%`` format); indeterminate mode hides
    the bar text since there's no meaningful percentage to show.
    """

    def __init__(self, message: str, parent=None, title: str = "Processing"):
        super().__init__(message, None, 0, 0, parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self._bar = self.findChild(QProgressBar)
        if self._bar is not None:
            # Start indeterminate — bar text hidden until set_progress flips
            # to determinate and a real percentage exists to display.
            self._bar.setTextVisible(False)
        self.show()

    def set_progress(self, completed: int, total: int, message: str = "") -> None:
        """Drive the bar from a ProgressSink. total=0 ⇒ indeterminate.

        Determinate mode applies a two-tone gradient QSS and shows ``%p%``
        inside the bar. Indeterminate mode clears the QSS so Fusion's
        animated busy indicator still works, and hides the bar text.
        Phase messages go to the label above the bar in both modes.
        """
        if total <= 0:
            if self.maximum() != 0 or self.minimum() != 0:
                self.setRange(0, 0)
            if self._bar is not None:
                self._bar.setTextVisible(False)
                self._bar.setStyleSheet("")
        else:
            if self.maximum() != total:
                self.setRange(0, total)
            self.setValue(min(completed, total))
            if self._bar is not None:
                # Reset format to the Qt default so %p% resolves even if
                # something upstream had set a custom format string.
                self._bar.setFormat("%p%")
                self._bar.setTextVisible(True)
                from src.gui.theme import get_progress_chunk_color, get_progress_groove_color
                chunk = QColor(get_progress_chunk_color())
                light = chunk.lighter(135).name()
                dark  = chunk.darker(125).name()
                mid   = chunk.name()
                self._bar.setStyleSheet(
                    "QProgressBar {"
                    f" background-color: {get_progress_groove_color()};"
                    " border: 1px solid rgba(0,0,0,0.25);"
                    " border-radius: 3px;"
                    " text-align: center;"
                    "}"
                    "QProgressBar::chunk {"
                    " background: qlineargradient("
                    "  x1:0, y1:0, x2:0, y2:1,"
                    f"  stop:0 {light},"
                    f"  stop:0.5 {mid},"
                    f"  stop:1 {dark}"
                    " );"
                    " border-radius: 2px;"
                    "}"
                )
        if message:
            self.setLabelText(message)


class FileLoaderWorker(QThread):
    """Worker thread for loading INI files without blocking UI.

    Loads configured sources from settings and emits the merged entries plus
    pre-computed sort keys so the main thread doesn't need to re-parse base.ini.
    """

    # (entries, default_values dict, pre-computed group sort keys)
    finished = pyqtSignal(list, dict, list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    progress_pct = pyqtSignal(int, int, str)  # (completed, total, message)

    # 3 phase boundaries: sources read → entries built → sort keys computed.
    _PHASE_TOTAL = 3

    def run(self):
        from src.gui.string_table_model import _group_sort_key
        try:
            logger.info("FileLoaderWorker starting...")
            self.progress_pct.emit(0, self._PHASE_TOTAL, "Reading source files...")
            self.progress.emit("Reading source files...")

            sources_dict, hierarchy, enhancements_key_categories = load_sources_from_settings()
            logger.info(f"Loaded from settings: sources={list(sources_dict.keys())}, hierarchy={hierarchy}")

            if not (sources_dict and hierarchy):
                raise ValueError("No sources configured")

            self.progress_pct.emit(1, self._PHASE_TOTAL, "Creating StringEntry objects...")
            self.progress.emit("Creating StringEntry objects...")
            entries = load_source_files(sources_dict, hierarchy, enhancements_key_categories=enhancements_key_categories)
            logger.info(f"load_source_files returned {len(entries)} entries")

            default_values = dict(sources_dict.get("global", {}))

            self.progress_pct.emit(2, self._PHASE_TOTAL, "Computing sort keys...")
            self.progress.emit("Computing sort keys...")
            sort_keys = [_group_sort_key(e.key) for e in entries]

            self.progress_pct.emit(3, self._PHASE_TOTAL, "Ready")
            logger.info("FileLoaderWorker finished successfully")
            self.finished.emit(entries, default_values, sort_keys)
        except Exception as e:
            logger.exception(f"Error loading files: {e}")
            self.error.emit(str(e))


class StartupSyncWorker(QThread):
    """Worker thread that syncs all enabled remote sources on startup.

    Uses conditional GET (If-Modified-Since) so only changed files are downloaded.
    Emits source_starting before each download, source_synced after, source_error on
    failure. Always emits finished so loading proceeds even when sources fail.
    """

    source_starting = pyqtSignal(str)        # source_name (about to sync)
    source_synced = pyqtSignal(str, bool)    # (source_name, was_updated)
    source_error = pyqtSignal(str, str)      # (source_name, error_message)
    finished = pyqtSignal()

    def run(self):
        from src.utils.updater import download_file_if_changed

        cache_dir = AppSettings.get_cache_dir()
        cache_mapping = {
            AppSettings.SOURCE_GLOBAL:      "base.ini",
        }

        for source_name in [
            AppSettings.SOURCE_GLOBAL,
        ]:
            if not AppSettings.is_source_enabled(source_name):
                continue
            if not AppSettings.get_source_auto_update(source_name):
                continue

            source_url = AppSettings.get_source_path(source_name)
            if not source_url or not source_url.startswith("http"):
                continue

            self.source_starting.emit(source_name)
            cache_file = cache_dir / cache_mapping.get(source_name, f"{source_name}.ini")
            try:
                updated = download_file_if_changed(source_url, cache_file)
                self.source_synced.emit(source_name, updated)
            except Exception as e:
                logger.warning(f"Startup sync failed for {source_name}: {e}")
                self.source_error.emit(source_name, str(e))

        self.finished.emit()


class EnhancementsGeneratorWorker(QThread):
    """Worker thread for generating enhancements INI files via generate_enhancements_ini.py."""

    progress = pyqtSignal(str)
    progress_pct = pyqtSignal(int, int, str)  # (completed, total, message)
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, categories: set[str] | None = None):
        super().__init__()
        self.categories = categories

    def run(self):
        import importlib.util
        import sys as sys_module
        from src.utils.dataforge_patcher import apply_patches
        try:
            if getattr(sys, 'frozen', False):
                script_path = Path(sys._MEIPASS) / 'scripts' / 'generate_enhancements_ini.py'
            else:
                script_path = Path(__file__).parent.parent.parent / 'scripts' / 'generate_enhancements_ini.py'

            if not script_path.exists():
                raise FileNotFoundError(f"Enhancements generator script not found: {script_path}")

            base_ini  = AppSettings.get_cache_dir() / 'base.ini'
            forge_dir = AppSettings.get_dataforge_cache_dir()
            # ── Diff-cache check ──────────────────────────────────────────────
            # Compare the current DataForge XMLs against the last-run manifest.
            # None  → no manifest yet, run everything.
            # set() → nothing changed, skip entirely.
            # {...} → only re-run the categories whose source XMLs changed.
            libs_dir = forge_dir / "raw" / "libs"
            diff = dirty_categories(libs_dir)
            if diff is not None:
                if not diff:
                    logger.info("Diff-cache: no DataForge changes detected, skipping enhancement generation.")
                    self.finished.emit(True)
                    return
                if self.categories is not None:
                    self.categories = self.categories & diff
                else:
                    self.categories = diff
                logger.info(f"Diff-cache: re-running categories {self.categories}")
            # ─────────────────────────────────────────────────────────────────
            # Re-apply DataForge patches before generation. apply_patches is
            # idempotent: already-patched files are a cheap no-op, so running
            # this every regen picks up newly-added patches without forcing
            # the user through a full re-extract. Bar stays indeterminate
            # here — ``mod.main()`` below takes over with determinate ticks
            # once its ProgressSink is wired up.
            self.progress_pct.emit(0, 0, "Applying DataForge patches…")
            self.progress.emit("Applying DataForge patches…")
            patch_report = apply_patches(
                resolve_patches_dir(), forge_dir,
                progress_callback=self.progress.emit,
            )
            logger.info(f"DataForge patches: {patch_report.summary_line()}")
            if patch_report.errors:
                for err in patch_report.errors:
                    logger.warning(f"  patch error: {err}")

            self.progress.emit("Loading enhancements generator...")

            module_name = "generate_enhancements_ini_worker"
            if module_name in sys_module.modules:
                del sys_module.modules[module_name]

            spec = importlib.util.spec_from_file_location(module_name, script_path)
            mod = importlib.util.module_from_spec(spec)
            sys_module.modules[module_name] = mod
            spec.loader.exec_module(mod)

            self.progress.emit("Generating enhancements (may take a few minutes on first run)...")
            logger.info("Enhancements generation worker: calling mod.main()")

            cat_desc = ", ".join(sorted(self.categories)) if self.categories else "all"
            logger.info(f"Enhancements generation: base_ini={base_ini}, forge_dir={forge_dir}, categories={cat_desc}")

            # Bridge the script's ProgressSink callback into a Qt-safe signal.
            # PyQt signal emits are thread-safe across QThread boundaries, so
            # this is safe to call from lookup-pool workers.
            def _on_progress(completed: int, total: int, message: str) -> None:
                self.progress_pct.emit(completed, total, message)

            mod.main(base_ini, forge_dir, categories=self.categories,
                     progress_callback=_on_progress,
                     patches_dir=resolve_patches_dir())
            logger.info("Enhancements generation worker: mod.main() completed successfully")

            self.finished.emit(True)
        except Exception as e:
            logger.exception(f"Enhancements generation failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False)


class P4kExtractWorker(QThread):
    """Worker thread for extracting global.ini from Data.p4k via unp4k.exe."""

    progress = pyqtSignal(str)   # status message
    progress_pct = pyqtSignal(int, int, str)  # (completed, total, message)
    finished = pyqtSignal(bool)  # True = success
    error = pyqtSignal(str)      # error message (emitted before finished(False))

    def __init__(self, p4k_path, output_path, unp4k_exe):
        super().__init__()
        self._p4k = p4k_path
        self._out = output_path
        self._exe = unp4k_exe

    def run(self):
        from src.utils.pak_extractor import extract_global_ini
        try:
            extract_global_ini(
                self._p4k, self._out, self._exe,
                progress_callback=self.progress.emit,
                progress_pct_callback=lambda c, t, m: self.progress_pct.emit(c, t, m),
            )
            self.finished.emit(True)
        except Exception as e:
            logger.exception(f"P4K extraction failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False)


class DataForgeExtractWorker(QThread):
    """Worker thread for extracting DataForge entity XMLs from Data.p4k."""

    progress = pyqtSignal(str)
    progress_pct = pyqtSignal(int, int, str)  # (completed, total, message)
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, p4k_path, unp4k_exe, unforge_exe, cache_dir):
        super().__init__()
        self._p4k       = p4k_path
        self._unp4k_exe = unp4k_exe
        self._unforge_exe = unforge_exe
        self._cache_dir = cache_dir

    def run(self):
        from src.utils.pak_extractor import extract_dataforge
        from src.utils.dataforge_patcher import apply_patches
        try:
            extract_dataforge(
                self._p4k,
                self._unp4k_exe,
                self._unforge_exe,
                self._cache_dir,
                progress_callback=self.progress.emit,
                progress_pct_callback=lambda c, t, m: self.progress_pct.emit(c, t, m),
            )
            # Apply declarative patches over known CIG data bugs so downstream
            # consumers (enhancement generator, future tooling) see corrected
            # data. Patch failures are recorded in the report but don't block
            # the pipeline.
            #
            # Flip the progress bar back to indeterminate (range 0-0, auto-
            # animating) so the user can see we're still working — after
            # extract_dataforge completes, the bar sits at its final 3/3
            # "Done" determinate state, which would look like the dialog is
            # about to close. The patches phase has no useful per-file
            # progress, so indeterminate is the honest signal.
            self.progress_pct.emit(0, 0, "Applying DataForge patches…")
            self.progress.emit("Applying DataForge patches…")
            patch_root = resolve_patches_dir()
            report = apply_patches(patch_root, self._cache_dir,
                                   progress_callback=self.progress.emit)
            logger.info(f"DataForge patches: {report.summary_line()}")
            if report.errors:
                for err in report.errors:
                    logger.warning(f"  patch error: {err}")
            self.finished.emit(True)
        except Exception as e:
            logger.exception(f"DataForge extraction failed: {e}")
            self.error.emit(str(e))
            self.finished.emit(False)


class SelectAllDelegate(QStyledItemDelegate):
    """Custom delegate for the Custom Value column.

    - Selects all text when the editor opens so typing overwrites but Esc keeps it.
    - Extends the editor's right-click menu with <EM3>/<EM4> wrap actions so
      authors can apply Star Citizen emphasis tags around the selected text.
    """

    def createEditor(self, parent, option, index):
        from PyQt6.QtWidgets import QLineEdit
        editor = super().createEditor(parent, option, index)
        if hasattr(editor, 'selectAll'):
            editor.selectAll()
        if isinstance(editor, QLineEdit):
            editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            editor.customContextMenuRequested.connect(
                lambda pos, ed=editor: SelectAllDelegate._show_editor_menu(ed, pos)
            )
        return editor

    @staticmethod
    def _show_editor_menu(editor, pos):
        menu = editor.createStandardContextMenu()
        menu.addSeparator()
        has_sel = editor.hasSelectedText()
        em3 = menu.addAction("Underline")
        em3.setEnabled(has_sel)
        em3.triggered.connect(lambda: SelectAllDelegate._wrap_selection(editor, "EM3"))
        em4 = menu.addAction("Highlight")
        em4.setEnabled(has_sel)
        em4.triggered.connect(lambda: SelectAllDelegate._wrap_selection(editor, "EM4"))
        menu.exec(editor.mapToGlobal(pos))

    @staticmethod
    def _wrap_selection(editor, tag: str):
        sel = editor.selectedText()
        if not sel:
            return
        # QLineEdit.insert replaces the current selection. Place the caret
        # just inside the closing tag so successive edits stay near the text.
        wrapped = f"<{tag}>{sel}</{tag}>"
        start = editor.selectionStart()
        editor.insert(wrapped)
        editor.setCursorPosition(start + len(f"<{tag}>") + len(sel))

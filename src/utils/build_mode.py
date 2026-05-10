"""Build-time mode flags.

PR-B in the standalone-build series. PR-C's build script
(`build_exe.py --portable`) overwrites this module with one that has
``IS_PORTABLE = True`` before PyInstaller bundles it. Default ships
False, so the un-built repo and the standard PyInstaller build both
behave identically (registry mode).

Portable mode changes two things at runtime:

  1. ``AppSettings._backend`` is set to a ``JsonSettings`` rooted at
     ``<user_data_dir>/config.json`` (PR-A's hook) instead of using
     ``QSettings`` against the Windows registry.
  2. ``AppSettings.get_user_data_dir()`` returns ``<exe-dir>/data/``
     (or ``<repo-root>/portable_data/`` when running unfrozen) so all
     cache / backups / user.ini live alongside the binary instead of
     under ``Documents\\Smart Citizen``.

Migrators that read the legacy registry tree are no-ops in portable
mode — there's no registry to migrate from.

Tests can flip ``IS_PORTABLE`` via ``monkeypatch.setattr`` to exercise
either branch without rebuilding. Production code should only ever
read ``IS_PORTABLE`` (never write to it outside the build script).
"""

# Resolution: prefer ``_build_info.IS_PORTABLE`` if present (written by
# the build script via ``build_exe.py --portable``); otherwise default
# to False (registry mode). Keeping the build-time flag in a separate
# generated module means the repo can stay clean — no on-disk diff
# between standard vs portable builds, no risk of accidentally
# committing IS_PORTABLE=True. The generated module is git-ignored.
try:
    from src.utils._build_info import IS_PORTABLE
except ImportError:
    IS_PORTABLE: bool = False  # type: ignore[no-redef]

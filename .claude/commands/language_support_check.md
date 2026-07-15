---
description: For every activated language, verify all user-facing UI strings and in-app docs have at least an AI translation
---

# /language_support_check

Audit translation coverage for every activated language. Catches the gaps the i18n fallback chain hides: a key that silently renders in English because it was never added to a language file, a new dialog whose strings were added to `english/ui.json` only, an in-app doc that never got a translated copy, and hardcoded literals that bypass `tr()` entirely and can never be translated.

Background: `tr()` resolves each key as `ht` (human translation), then `at` (AI translation), then the English base value, then the bare key. "Has at least the AI translation" means every key shows *something* in the selected language: `ht` or `at` non-empty. Provenance rules live in `languages/TRANSLATIONS.md`.

## Policy constraints (read before drafting anything)

- **Never edit or overwrite a non-empty `ht`.** Human translations are only ever replaced by better human translations.
- **AI backfill happens only at pre-release docs-sync time, with explicit confirmation.** This command surfaces gaps; it does not fill them unless the user says so at the checkpoint.
- New AI translations go in `at` (leave `ht` empty) so the inline provenance stays truthful and translators can find them with `grep '"ht": ""'`.

## Inputs

- `languages/<lang>/ui.json` for every activated language. Activated = what `AppSettings.get_available_languages()` (`src/utils/settings.py`) offers: English plus any folder whose `ui.json` carries at least one translation. `languages/english/ui.json` is the key universe; every leaf there is a key the UI can request.
- `languages/<lang>/HELP.md`, `ABOUT.md`, `LEGAL.md`: per-language in-app docs, resolved by `AppSettings.get_localized_doc_path()`. A missing file falls back to the English `docs/` copy.
- `languages/sources.json`: per-language base.ini download URL for game strings.
- `installer.iss`: the `LanguageChoicePage` option list and the `selected_language` registry write-back values.
- `src/gui/*.py`: user-facing literals, to catch strings not routed through `tr()`.
- `SmartCitizen.spec` and `scripts/build/build_exe.py`: both bundling lists must ship the `languages/` tree (a file present in the repo but missing from either list breaks only the frozen build).

## Checks

1. **Key parity per language** *(Major)*: for each activated non-English language, diff its `ui.json` key set against `languages/english/ui.json`. Flag every key that is missing entirely, and every key present with both `ht` and `at` empty. Either way the user sees English. A quick way to compare: load both files with `json.load` and walk the dot-paths; do not trust line counts.

2. **Untranslatable literals** *(Major)*: grep `src/gui/` (and `src/utils/` where user-visible messages originate, e.g. workers and dialogs) for user-facing string literals not wrapped in `tr()`: window/dialog titles, button and menu labels, status-bar messages, message-box text. These can never be translated regardless of ui.json coverage. Ignore log-only strings, exception text, and developer-facing output.

3. **In-app doc coverage** *(Major)*: each activated non-English language should ship `HELP.md`, `ABOUT.md`, and `LEGAL.md` under `languages/<lang>/`. Flag each missing file (the user gets the English fallback). Where a translated copy exists, spot-check that its section structure still matches the English original in `docs/` (a doc translated three releases ago may describe removed features; defer deep content drift to `/docs_sync_check`).

4. **Tutorial coverage** *(Major)*: the guided tour reads its strings from `tutorial.*` keys in ui.json. Confirm every activated language covers the full `tutorial.*` subtree; a first-launch tour that flips to English mid-way reads as broken.

5. **Installer sync** *(Critical)*: the `LanguageChoicePage` options and the `selected_language` write-back case in `installer.iss` must exactly match the activated language set and the folder names under `languages/` (e.g. `portuguese_br`). A drift either offers a language the app cannot render or strands a real language behind the unknown-saved-value guard.

6. **Game-string source mapping** *(Critical)*: every activated non-English language needs an entry in `languages/sources.json` (its base.ini download URL). Without one, selecting the language leaves the table empty until the user manually maps a URL.

7. **Stub hygiene** *(Minor)*: a `languages/` folder whose `ui.json` has no translations should stay hidden by `get_available_languages()`. Confirm the stub-detection still holds for any new folder, and that no activated language regressed to stub state.

8. **Bundling** *(Critical if a new per-language file was added this cycle, else skip)*: confirm `languages/` (including any newly added per-language docs) is covered by **both** `SmartCitizen.spec` and `scripts/build/build_exe.py`. A miss here ships a frozen build that shows raw `tr()` keys or English docs while the dev run looks fine.

## Output

Group findings by severity. Within each group: `language → file — short description (count where relevant)`.

```
**Critical**:
  spanish → languages/sources.json — no base.ini URL mapping; game strings cannot download

**Major**:
  spanish → languages/spanish/HELP.md — missing; in-app Help falls back to English
  french → ui.json — 12 keys missing vs english (dialogs.unapplied_changes_*, toolbar.apply_enabled_tooltip, ...)
  (untranslatable) → src/gui/import_dialog.py:88 — "Import Conflicts" title is a literal, not tr()

**Minor**:
  french → ui.json — 93 keys AI-translated only (ht empty); fine for release, list for human review
  portuguese_br → ui.json — 3 stale keys no longer in english/ui.json
```

For the AI-only counts (Minor), report the number per language, not the full key list, unless the user asks.

End with a one-line **verdict**:

- **Clean**: every activated language fully covers the English key universe (ht or at), docs and installer and sources.json all in sync.
- **Minor issues**: only AI-only coverage or stale-key findings.
- **Needs attention**: any Critical or Major findings.

**CHECKPOINT — present the findings and ask before changing anything.** If the user approves backfill: fill `at` only (never `ht`), add missing keys with English-derived AI translations, draft missing doc translations as new files, and note the work in `languages/TRANSLATIONS.md` per its workflow section. Remind the user that human review candidates are exactly the `"ht": ""` keys.

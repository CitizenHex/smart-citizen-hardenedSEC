# Translation Provenance

This file tracks which UI strings are human-translated and which were machine-backfilled, so human translators know exactly what to review. The policy:

- **Human translations are never edited or overwritten by AI.** They are only ever replaced by a better human translation.
- At pre-release, any string still missing from an exposed language is backfilled with an AI translation (trained on the file's existing human translations for register and terminology) so no shipped language shows raw English. Those keys are listed below.
- **Translators:** when you re-translate an AI-backfilled key, move it from the AI list here to the human note for that language. That is the whole workflow.

The guided tour lives in `assets/tutorial.json` (English) and is translated per language under the `tutorial.*` keys in each `ui.json`. English itself has no `tutorial.*` section, so the English-vs-translation key diff is expected to show those keys as "extra".

## english

Source language. All strings authored by the maintainer.

## french

Human-translated by **Akwa**, with the process led by **Ishikudeska**, except the AI-backfilled keys below (Claude Opus 4.8, 2026-06-04, styled on the existing human strings: vous register, French spacing before `:` `;` `?`, guillemets):

- `toolbar.more_btn`
- `strings_tab.context_underline`, `strings_tab.context_highlight`
- `config.map_language_btn`, `config.map_language_title`, `config.map_language_desc`
- `config.migrate_data_title`, `config.migrate_data_body`, `config.migrate_data_done_title`, `config.migrate_data_done_body`, `config.migrate_data_failed_title`, `config.migrate_data_failed_body`
- `dialogs.language_downloading`, `dialogs.language_no_url`, `dialogs.language_download_failed`, `dialogs.language_generating_enhancements`
- `dialogs.file_not_found_title`, `dialogs.file_not_found_body`, `dialogs.empty_file_title`, `dialogs.empty_file_body`
- `dialogs.copy_filtered_title`, `dialogs.copy_filtered_empty`, `dialogs.copy_filtered_done`, `dialogs.copy_error_title`, `dialogs.copy_error_body`
- `tutorial.*` (all 18 guided-tour steps; the tour was never human-translated)
- `progress.*` (all 16 progress-bar strings shown during loading, extraction, and enhancement generation)
- `HELP.md`, `ABOUT.md`, `LEGAL.md` in this folder (full-document AI translations of the in-app docs; each carries a note that the English version governs)

## portuguese_br

Human-translated by **Nxzzin**, with the process led by **Ishikudeska**, except the AI-backfilled keys below (Claude Opus 4.8, 2026-06-04, styled on the existing human strings: você register, smart quotes for UI references):

- Same key list as french: `toolbar.more_btn`, `strings_tab.context_underline`, `strings_tab.context_highlight`, the `config.map_language_*` and `config.migrate_data_*` groups, the `dialogs.language_*` group, `dialogs.file_not_found_*`, `dialogs.empty_file_*`, the `dialogs.copy_*` group, `tutorial.*` (all 18 steps), `progress.*` (all 16 strings), and the `HELP.md` / `ABOUT.md` / `LEGAL.md` documents in this folder.

## spanish

Stub only (`_comment`, no translations). Hidden from the language selector until human translations land. No AI backfill: a fully machine-translated language is not something we ship as "available".

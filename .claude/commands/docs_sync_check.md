---
description: Verify user-facing strings, HELP / ABOUT docs, README, and the tutorial match the current app
---

# /docs_sync_check

Cross-check the running app's user-facing surface against the docs and tutorial. Catches drift introduced when a button is renamed in code but the doc still describes the old name, when a control is removed but the tutorial still points at it, or when a new feature ships without a docs update.

## Severities

- **Critical** — a tutorial step in `src/gui/coach_mark.py` references a widget that no longer exists. Will crash or confuse first-time users.
- **Major** — workflow steps in `docs/HELP.md` no longer match the code, or a user-facing string is described in `docs/HELP.md` / `docs/ABOUT.md` under a name that no longer exists in code.
- **Minor** — a feature mentioned in `docs/ABOUT.md` or `README.md` has been removed/renamed but isn't user-facing-critical (e.g. a string label drift that still reads naturally).

## Inputs

- `src/gui/*.py` — user-facing strings (window titles, button/menu/tab labels, dialog text, log lines users see in the Log Tab).
- `docs/HELP.md` — step-by-step user instructions.
- `docs/ABOUT.md` — feature summary.
- `src/gui/coach_mark.py` — `CoachMarkStep` entries that drive the guided tour.
- `README.md` — Features section and Screenshots labels.

## Checks

1. **Tutorial widget validity** *(Critical)*: every `CoachMarkStep` in `coach_mark.py` references a target widget — confirm the widget still exists (grep for its attribute name on `MainWindow` and the relevant tabs). Flag any step whose target was deleted or renamed.
2. **String drift in HELP/ABOUT** *(Major)*: pull every user-facing literal from `src/gui/` and check whether any noun phrase used in `HELP.md` or `ABOUT.md` is no longer present in the code (likely renamed). Flag with the doc file:line plus the suspected new wording from the code.
3. **Workflow currency** *(Major)*: `HELP.md` describes Apply / Restore / Extract / Reset user.ini / Export Loc-Pack / channel switch. If a recent diff changed any of these flows, surface the matching section of `HELP.md` for review.
4. **Feature parity** *(Minor, escalate to Major if HELP.md has a how-to step for the affected feature)*: `HELP.md`, `ABOUT.md`, and README's Features list should match the code. Flag features described in docs that no longer exist, and code features that aren't surfaced in any of the three.

## Output

Group findings by severity. Within each group: `doc-file:line → code-file:line — short description`.

```
**Critical** (tutorial broken):
  src/gui/coach_mark.py:54 → (widget removed) — TutorialTour step "Click Extract" targets MainWindow.extract_btn which no longer exists

**Major** (should fix):
  docs/HELP.md:120 → src/gui/main_window.py:380 — HELP describes "Reset Overrides" button; code now labels it "Reset user.ini"

**Minor** (consider):
  README.md:24 → (no code reference) — Features list mentions "auto-update for source INIs" but the URL-source pipeline was retired in 0.7.0
```

End with a one-line **verdict**:

- **Clean** — no findings.
- **Minor issues** — only Minor findings.
- **Needs attention** — any Critical or Major findings.

After the verdict, **CHECKPOINT — pause and ask the user whether to draft doc updates for the Critical/Major findings, or move on.** Do not edit docs without confirmation — surface, don't auto-correct.

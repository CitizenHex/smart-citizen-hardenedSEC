# Contributor Guide

How to set up Smart Citizen for local development.
## TLDR

1) Use Claude code to check out the repo.
2) Tell it to view and describe the issues listed [here](https://github.com/Osiris-DevWorks/smart-citizen/issues?q=is%3Aissue%20state%3Aopen%20label%3A2.2.0%20no%3Aassignee) to you.
3) Pick an issue that interests you and use the `/begin_work` Claude command to begin work. So for example "/begin_work [issue number or issue link] and then just go through the process. 
4) When you think it's done, do the `/pull_request` command. 
5) It will be reviewed by the repo owner. Resolve any requested changes, then it will be merged into the release branch.

## Prerequisites

- Python 3.9+ (recommended 3.10+)
- Windows 10/11 (the app uses Windows Registry and is Win32-only)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Osiris-DevWorks/smart-citizen.git
   cd smart-citizen
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python src/main.py
   ```

## Going deeper

For architecture, conventions, and design decisions, see [`CLAUDE.md`](../CLAUDE.md) at the repo root and the per-directory `CLAUDE.md` files it points to.

## PR scope and size

Keep PRs **scoped to a single concern** to minimize review burden. A well-scoped PR's title fits on one line without "and" or a semicolon, and the diff tells a single story.

**One PR per:**

- A single feature.
- A single bug fix.
- A batch of *related* bug fixes (same subsystem, same release-branch scope).
- A self-contained refactor.
- A self-contained doc update.

**Don't bundle:**

- A feature and unrelated bug fixes.
- A refactor and a feature built on top of it — land the refactor first, ship, then build on the cleaned-up base.
- Doc updates unrelated to the code change in the same PR.
- "Drive-by" cleanups in files you didn't otherwise need to touch.

**Size signals** — if any of these is true, consider splitting:

- Diff exceeds ~400 net lines of change (excluding generated files and lock files).
- More than 8 files touched outside a deliberate cross-cutting change (project-wide rename, doc reorganization, dep bump).
- The PR title needs "and" or a semicolon to describe both concerns.
- A reviewer would need to context-switch between two mental models to read it.

When splitting is impractical (e.g. a refactor that genuinely needs to touch many files), call it out in the PR description so reviewers know what to focus on. These thresholds are calibration, not laws — a focused 500-line PR is easier to review than two 200-line PRs that overlap.

The `/pull_request` slash command surfaces scope signals automatically but never auto-splits; the call is yours.

## AI Usage

If you're using Claude Code (or another AI coding assistant) on Smart Citizen, follow Anthropic's [Claude Code best practices](https://code.claude.com/docs/en/best-practices). TL;DR:

- **Read the per-directory `CLAUDE.md` for the layer you're touching before editing.** The root `CLAUDE.md` indexes them. They are the project's contract for conventions.
- **Explore → plan → code.** Use plan mode for non-trivial changes; skip it for typos and one-liners.
- **Be specific in prompts.** Reference files with `@`, name the failing test, point at example patterns. Vague prompts produce vague code.
- **Give the model a way to verify.** Run `pytest tests/` for logic changes; load the app (`python src/main.py`) for GUI changes. Manual smoke testing is the only verification path for the `QThread` workers.
- **Address root causes, not symptoms.** Don't suppress errors to make a test pass — fix the underlying issue.
- **Course-correct fast.** `Esc` to interrupt, `/rewind` to roll back, `/clear` between unrelated tasks. After two failed corrections, restart with a sharper prompt.
- **Use subagents for exploration.** They report back summaries instead of consuming the main context with dozens of file reads.
- **Keep `CLAUDE.md` lean.** If a rule isn't earning its weight, prune it. Bloated files cause real instructions to get ignored.
- **Match the branching model.** PRs target the active `release/X.Y.Z` integration branch, not `main` (see root `CLAUDE.md` → *Version & Release*).

Full reference: <https://code.claude.com/docs/en/best-practices>

## Slash commands for repo standards

The project ships a set of Claude Code slash commands under `.claude/commands/` that enforce documented standards. Each runs with **CHECKPOINTS** between major steps — they pause and wait for your confirmation before continuing, matching the root `CLAUDE.md` *Communication style* rule.

- **`/pull_request`** — open the current branch as a **draft** PR, then run the standards self-review (test coverage → docs/tutorial sync → standards spot-check) one section at a time with checkpoints between, and offer to mark the PR ready when you're satisfied. Body includes a Testing Checklist, a *Testing performed* block (`--testing "description"` flag flows in here), a *Post-merge QA* checklist, and an attribution footer. `--skip-draft` opens the PR as ready-for-review and skips the walkthrough.
- **`/standards_check`** — lint the current diff against documented conventions (direct `QSettings` calls, hard-coded column indices, worker progress, DataForge subtree coverage, DRY, etc.). Findings are grouped **Critical / Major / Minor** with a one-line verdict (**Clean / Minor issues / Needs attention**); pauses at the end before any auto-fix.
- **`/docs_sync_check`** — surface drift between `src/gui/` user-facing strings and `docs/HELP.md` / `docs/ABOUT.md` / `src/gui/coach_mark.py` / README Features. Same severity-grouped + verdict output; pauses at the end.
- **`/test_coverage_check`** — audit branch changes for matching tests under `tests/`, with the documented exemption rules (`QThread` workers, GUI wiring, `scripts/`). Findings severity-grouped (Critical missing test / Major stale test / Minor exempt-flag); runs `pytest tests/` and ends with the verdict + checkpoint.
- **`/start_release major|minor|patch`** — open the next `release/X.Y.Z` integration branch off `main`, bump `VERSION.TXT`, and commit the kickoff. Pauses for confirmation before the branch-create. Local only; you push when ready.
- **`/begin_work <issue-url-or-#NN> <X.Y.Z|major|minor|patch>`** — start work on a GitHub issue. Reuses an existing unmerged `release/X.Y.Z` when one fits, otherwise opens a new one via the `/start_release` procedure, then creates a feature branch (`issue/<NN>-<slug>`) off the release branch. After setup, **plans the implementation in chunks** with a CHECKPOINT after each, **implements chunk-by-chunk** with diffs shown between, and ends with a step-by-step walkthrough before suggesting `/pull_request`.
- **`/pre_release`** — pre-merge gate before shipping an integration branch. Runs the three quality checks (test coverage → docs sync → standards) and a fourth **contributor acknowledgement audit** that diffs the git log against `docs/ABOUT.md` and `README.md` to surface any code contributor not yet credited. CHECKPOINTs between every step; ends with an overall release-readiness verdict.
- **`/review_pr <N | URL | current>`** — structured review of a single PR. Gathers context (PR metadata, full diff, comments, linked GitHub issue), summarizes, then walks every changed file in Smart Citizen's layer-dependency order (models → parser → merger → utils → gui → scripts → tests → docs → config) with a CHECKPOINT after each. Per-file findings are severity-tagged and linked back to the relevant `CLAUDE.md` section. Final verdict is *Approve / Request Changes / Comment*; never posts to GitHub without explicit confirmation.

`/pull_request` rolls up the three quality checks into one driven walkthrough; the focused commands are useful mid-work without opening a PR. `/start_release` is the branching kickoff per the documented release model. `/begin_work` is the typical entry point when picking up a GitHub issue — it handles release-branch resolution, planning, and step-by-step implementation for you. `/pre_release` is the final gate before merging `release/X.Y.Z` to `main`.

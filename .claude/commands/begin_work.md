---
description: Start work on a GitHub issue — load context, get on the right release branch (creating it if needed), open a feature branch, then plan and implement step-by-step with check-ins
---

# /begin_work

Bootstrap a work session for a GitHub issue. Resolves which `release/X.Y.Z` integration branch holds the work — reusing an existing unmerged branch when one fits, otherwise opening a new one by following the `/start_release` procedure — then creates a feature branch off it for the issue. After setup, drives the work in chunks with checkpoints between each stage so the user stays in the loop.

Work through every step in order. After each step, stop at the **CHECKPOINT** and wait for the user before proceeding.

## Arguments

`$ARGUMENTS` — two whitespace-separated tokens, both required:

1. **issue** — a GitHub issue URL (`https://github.com/Osiris-DevWorks/smart-citizen/issues/NN`) or short form (`#NN`). The repo is implicit (`Osiris-DevWorks/smart-citizen`).
2. **target release** — either an explicit semver `X.Y.Z` (e.g. `1.4.3`) or a bump type (`major` / `minor` / `patch`).

If either argument is missing or malformed, abort with: *"/begin_work requires: <issue-url-or-#NN> <X.Y.Z | major | minor | patch>"*

## 1. Parse and validate arguments
- Extract the issue number from URL or `#NN` shorthand.
- Validate the target release:
  - Matches `^\d+\.\d+\.\d+$` → treat as explicit version.
  - Is `major` / `minor` / `patch` → compute the explicit version from current `VERSION.TXT` (same math as `/start_release`).
  - Otherwise abort.

## 2. Fetch and summarize the issue

```bash
gh issue view <NN> --json number,title,body,labels,state,url
```

- If `state` is `closed`, warn the user.
- Present a short summary: number, title, state, labels, and a one-paragraph summary of the body (keep it tight — the full body is in conversation context).

**CHECKPOINT — confirm the issue summary captures the work, or correct it.** Wait for the user.

## 3. Resolve the target release branch

Target is `release/X.Y.Z` (the version from step 1). Check the world in this order:

- **Already merged to main**: `git branch -r --merged origin/main | grep -F "origin/release/X.Y.Z"`. If matched, abort — *"release/X.Y.Z is already merged to main; pick a higher target."*
- **Exists locally**: `git rev-parse --verify release/X.Y.Z`. If yes, `git checkout release/X.Y.Z`. Confirm `VERSION.TXT` on it equals `X.Y.Z`.
- **Exists on origin only**: `git ls-remote --heads origin release/X.Y.Z`. If matched, `git fetch origin release/X.Y.Z:release/X.Y.Z`, then check out. Confirm `VERSION.TXT`.
- **Does not exist anywhere**: open it by following the procedure in `.claude/commands/start_release.md`. Use the bump type the user passed; if they passed an explicit version, derive the bump type by diffing current `VERSION.TXT` (on `main`) against `X.Y.Z`. The derived bump must be a **single step** (next patch, next minor, or next major). If the requested version skips ahead (e.g. current `1.4.2` → requested `1.6.0`), abort and ask the user to clarify intent.

**Multi-active guard**: before creating a new release branch, run `git branch -a --list 'release/*' --no-merged origin/main`. If any other unmerged `release/*` exists, surface it and ask the user to confirm.

After this step you must be checked out on `release/X.Y.Z` with a clean working tree.

**CHECKPOINT — confirm the release branch is correct (reused / newly created) before opening the feature branch.** Wait for the user.

## 4. Create the feature branch

- Slug the issue title: lowercase, replace non-alphanumerics with `-`, collapse repeats, trim to ~40 chars.
- Branch name: `issue/<NN>-<slug>` (example: `issue/42-fix-channel-switch-race`).
- Create it: `git checkout -b issue/<NN>-<slug>` from the release branch.

Report:
- `Issue: #<NN> — <title>` (with URL)
- `Release branch: release/X.Y.Z` (note whether reused or newly created via /start_release)
- `Feature branch: issue/<NN>-<slug>`
- Scope reminder if `release/X.Y.Z` is a patch: *"Patch branches accept only bug fixes and minor polish — flag scope mismatch if this issue is feature work."*

**CHECKPOINT — ready to plan the work?** Wait for the user.

## 5. Plan the work

Before writing any code:

1. Identify which layers this issue touches. Pull the relevant per-directory `CLAUDE.md` into context (`src/gui/`, `src/utils/`, `src/parser/`, `src/merger/`, `src/models/`, `scripts/`, `tests/` — see root `CLAUDE.md` → *Per-directory guides*).
2. Propose the implementation in **manageable chunks**. One concept at a time per the root `CLAUDE.md` *Communication style* rule. For each chunk, present:
   - What you'll change and why.
   - The file(s) involved (with paths).
   - Any trade-offs the user should decide on.
   - **CHECKPOINT — wait for the user to confirm this chunk before moving to the next.**
3. After every chunk is confirmed individually, ask the user to approve the full plan as a whole.

**CHECKPOINT — full plan approved?** Wait for the user.

## 6. Implement step-by-step

Once the plan is approved:

- Implement one chunk at a time, in the order from the plan.
- After each chunk, show the diff for that chunk and pause.
- **CHECKPOINT — wait for the user to confirm this chunk before moving to the next.**
- Tests live in `tests/`. Run `pytest tests/` after any chunk that affects testable code and report the result.

## 7. Final walkthrough

When all chunks are implemented:

1. Run `/standards_check`, `/docs_sync_check`, and `/test_coverage_check` in sequence. Walk the user through findings.
2. Give a step-by-step walkthrough of everything that changed:
   - Files modified, grouped by layer (GUI / utils / parser / tests / docs).
   - Why each change was made (link back to the plan chunk).
   - What tests were added or updated.
   - Anything left intentionally untouched and why.

**CHECKPOINT — ready to run `/pull_request`?** Wait for the user.

## Notes

- The release branch (if newly created) and the feature branch are both local-only. The user pushes when ready.
- This command does not open a PR. `/pull_request` does — and now opens it as draft, so the user can keep iterating after the initial open.
- If the issue requires an exploratory spike that will not ship, this is the wrong command — work on a personal branch off `main` instead.

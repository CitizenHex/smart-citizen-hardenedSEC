---
description: Ship the active release/X.Y.Z — build the installer, merge to main, tag, push, and publish the GitHub release. Run after /pre_release passes.
---

# /ship_release

Walk the release-ship sequence with checkpoints between each step. Several steps are destructive (merge to `main`, tag, push) or have external side effects (publish GitHub release) — confirm before each.

Run **after** `/pre_release` returns a clean verdict. This command performs the merge-to-`main` handoff, builds the installer, publishes the GitHub release, and offers to open the next integration branch.

Work through every step in order. After each step, stop at the **CHECKPOINT** and wait for the user before continuing.

## Preflight

**This command ships whichever `release/X.Y.Z` branch the user is currently on** — the branch is the input. If multiple release branches exist, the user is responsible for being on the right one before invoking. Don't try to disambiguate.

Stop on the first failure.

- **On a release branch**: `git branch --show-current` must match `release/X\.Y\.Z`. Extract `X.Y.Z` for use below — this is the version we're shipping. Abort otherwise: *"Switch to the release branch you want to ship before running /ship_release."*
- **Surface other open release branches** (advisory): list any other `release/*` branches that exist locally or on origin. If found, print: *"Other release branches exist: <list>. Shipping `release/X.Y.Z` based on current branch — confirm this is the one you mean."* Wait for explicit confirmation before continuing the preflight.
- **Clean working tree**: `git status --porcelain` must be empty. Abort and list offending files otherwise.
- **VERSION.TXT matches branch**: read `VERSION.TXT`, strip whitespace, confirm it equals `X.Y.Z`. Abort with the mismatch otherwise.
- **Up to date with origin** (best-effort): `git fetch origin release/X.Y.Z`; if `git rev-list --count release/X.Y.Z..origin/release/X.Y.Z` > 0, abort: *"Local release branch is behind origin. Pull before shipping."* Skip silently if fetch fails (offline).
- **Pre-release was run recently** (advisory only): grep recent shell history or commit log for `/pre_release`; if no signal, remind the user: *"Heads-up: `/pre_release` doesn't appear to have run on this branch in the recent session. The ship sequence assumes it passed. Continue?"* Don't block.

**CHECKPOINT — preflight passes. Ready to build the installer for `vX.Y.Z`?** Wait for the user.

## 1. Build the installer

The build produces two artifacts: a PyInstaller onedir build and an Inno Setup installer (`.exe`) that wraps it.

### 1a. PyInstaller onedir build

```bash
.venv/Scripts/python.exe scripts/build/build_exe.py
```

Run from the repo root. Output lands in `dist/SmartCitizen/`. If the build fails, abort and surface the error — usually a missing dependency or a hook/spec drift.

### 1b. Inno Setup installer

Inno Setup is per-user; invoke via PowerShell with the full ISCC path:

```bash
powershell -NoProfile -Command "& 'C:\Users\<USERNAME>\AppData\Local\Programs\Inno Setup 6\ISCC.exe' installer.iss"
```

Substitute the current Windows username. Output: `dist/SmartCitizen-X.Y.Z-Setup.exe`. If ISCC isn't found at that path, ask the user where it's installed before proceeding.

Confirm `dist/SmartCitizen-X.Y.Z-Setup.exe` exists after the compile. Capture its size.

**CHECKPOINT — installer built at `dist/SmartCitizen-X.Y.Z-Setup.exe` (N MB). Test it manually before continuing.** Wait for the user to confirm they've installed and smoke-tested the build. Do not proceed without explicit go.

## 2. Merge release branch to main

This is destructive — once `main` advances and tags are pushed, the release is effectively shipped. Confirm before each git command in this section.

### 2a. Update main locally

```bash
git checkout main
git pull origin main
```

If the pull merges (i.e. `main` diverged unexpectedly), surface that and ask — do not continue automatically.

### 2b. Merge the release branch

```bash
git merge --no-ff release/X.Y.Z -m "Merge release/X.Y.Z into main"
```

`--no-ff` preserves the release branch's history as a discrete merge commit. If merge conflicts arise, abort and ask the user to resolve manually — do not attempt automated conflict resolution at this stage.

### 2c. Tag the release on main

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

### 2d. Push branch and tag

```bash
git push origin main
git push origin vX.Y.Z
```

Do these as two separate pushes so a tag-push failure doesn't leave `main` in a half-pushed state.

**CHECKPOINT — `main` is now at `vX.Y.Z` on origin. Ready to publish the GitHub release?** Wait for the user.

## 3. Publish the GitHub release

### 3a. Locate release notes

Look in this order:
1. `docs/X.Y.Z-RELEASE-NOTES.md` (post-1.4.1 convention)
2. `X.Y.Z-RELEASE-NOTES.md` at repo root (legacy)
3. Prompt the user — if neither exists, ask whether to draft a stub now or skip notes for this release. Don't fabricate notes.

If notes exist, verify the SAC banner is present at the top per project memory (every Smart Citizen X.Y.Z-RELEASE-NOTES.md needs the Smart App Control workaround). If missing, surface that and ask whether to add it.

### 3b. Create the release with installer attached

```bash
gh release create vX.Y.Z dist/SmartCitizen-X.Y.Z-Setup.exe \
  --title "Smart Citizen vX.Y.Z" \
  --notes-file <notes-path>
```

If no notes file resolved, prompt for an inline `--notes` body and use that, or fall back to `--generate-notes`.

The Discord webhook fires from `.github/workflows/release.yml` automatically when `DISCORD_RELEASE_WEBHOOK_URL` is configured; no manual ping needed.

**CHECKPOINT — release `vX.Y.Z` published with installer attached. Discord webhook will fire from CI.** Wait for the user.

## 4. Open the next integration branch

Offer to run `/start_release patch` to open the next bug-fix-scoped branch immediately. Most ships are followed by a patch branch as the new integration target. If the user wants `minor` or `major` instead, defer to them.

Ask: *"Open the next branch now? `patch` is the typical default — gives you `release/X.Y.(Z+1)` for the next round of bug fixes. Reply `patch`, `minor`, `major`, or `skip`."*

On `skip`, just report that the release is shipped and remind the user the next integration target needs to exist before any new work lands.

On any bump arg, defer to `/start_release` with that arg.

## Final report

Print:
- `Shipped vX.Y.Z`
- `Installer: dist/SmartCitizen-X.Y.Z-Setup.exe (<size>)`
- `Release URL: <gh release view url>`
- `Next integration branch: release/X.Y.(Z+1)` (if opened) or `(none yet — open one before starting new work)`
- Reminder: smoke-test the published installer download once GitHub finishes processing.

## Notes

- This command performs destructive git operations (`merge`, `tag`, `push`) and external publishes (`gh release create`). Every checkpoint exists because the prior step is the last reversible point. Honor them.
- Never combine the merge, tag, and push into a single non-interactive run. The user is the gate.
- The installer build (step 1) happens **before** the merge (step 2) so a build break doesn't leave `main` advanced past a non-shippable artifact.
- Tester pre-release installers (`installer-preview.yml`) are a separate flow and don't replace this command — they produce throwaway artifacts; this command produces the canonical release.

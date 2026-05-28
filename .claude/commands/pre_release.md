---
description: Pre-release sanity check before merging release/X.Y.Z to main — runs quality checks, security review, and contributor-acknowledgement audit
---

# /pre_release

Run before merging the active `release/X.Y.Z` integration branch to `main`. This is the final gate before the release ships — it confirms code quality, doc currency, test coverage, and that every code contributor is acknowledged in the project's in-app About and the README.

Work through every step in order. After each step, stop at the **CHECKPOINT** and wait for the user before continuing.

## Preflight

- Confirm the current branch is `release/X.Y.Z`. If not, abort and ask the user to switch.
- Confirm working tree is clean (`git status --porcelain`). If dirty, abort.
- Confirm `VERSION.TXT` matches `X.Y.Z`. If mismatched, surface the discrepancy and ask the user before proceeding.

**CHECKPOINT — preflight confirms release branch is ready for audit. Proceed?** Wait for the user.

## 1. Test coverage check

Follow the procedure in `.claude/commands/test_coverage_check.md`. Present findings grouped by severity (Critical / Major / Minor) and end with the verdict line.

**CHECKPOINT — ready for the next check?** Wait for the user.

## 2. UI / docs / tutorial sync check

Follow the procedure in `.claude/commands/docs_sync_check.md`. Present findings grouped by severity and end with the verdict line.

**CHECKPOINT — ready for the next check?** Wait for the user.

## 3. Standards spot-check

Follow the procedure in `.claude/commands/standards_check.md`. Present findings grouped by severity and end with the verdict line.

**CHECKPOINT — ready for the next check?** Wait for the user.

## 4. Security review

Run `/security-review` on the pending changes. Present findings grouped by severity and end with the verdict line.

**CHECKPOINT — ready for the contributor audit?** Wait for the user.

## 5. Contributor acknowledgement audit

Verify every code contributor is acknowledged in `docs/ABOUT.md` and `README.md`.

### 4a. Build the contributor list

Pull every author who has committed code:

```bash
git log --format='%aN|%aE' --no-merges | sort -u
```

Also pull GitHub-known contributors (gives the linkable login):

```bash
gh api "repos/Osiris-DevWorks/smart-citizen/contributors" --paginate --jq '.[] | {login: .login, contributions: .contributions}'
```

**Filter out**:
- The repo owner `Osiris-DevWorks` / `Osiris DevWorks` — already credited as the maintainer.
- AI co-author trailers (`Claude`, `noreply@anthropic.com`, anything tagged `Co-Authored-By: Claude*`) — these are not collaborators.
- Bot accounts (`dependabot[bot]`, `github-actions[bot]`, `*[bot]`, etc.).
- Anonymous commits with no name or only an email and no associated GitHub login.

Normalize: when a person has committed under multiple display-name/email combinations, merge them into one entry. If unsure, surface the duplicates and let the user decide.

### 4b. Pull the current acknowledgement set

Read both:

- `docs/ABOUT.md` — the in-app About panel content. Find the **Acknowledgments** section (or equivalent — section names may vary; look for headers containing "Acknowledg", "Credits", "Thanks").
- `README.md` — the `## Acknowledgments` section (and any `### Supporters` subsection).

Build a normalized set of names. Match against the contributor list using both display name and GitHub login where known.

### 4c. Categorize each missing contributor

For every contributor not currently acknowledged in **both** files (ABOUT.md and README.md):

- Pull their commit count: `git log --author='<email>' --no-merges --oneline | wc -l`
- Pull a sample of files they touched: `git log --author='<email>' --no-merges --name-only --pretty=format: | sort -u | head -10`
- Categorize:
  - **Substantial code contributor**: ≥3 commits OR touched non-trivial source files (anything under `src/`, `scripts/`, or `tests/`).
  - **Drive-by fixer**: 1–2 commits, only trivial files (README typo, comment fix, whitespace).

### 4d. Report

Group missing contributors by significance:

```
**Missing — substantial contributors** (suggest adding):
  Jane Doe (@janedoe) — 12 commits — touched src/gui/, src/utils/
  John Smith (@johnsmith) — 8 commits — touched scripts/

**Missing — drive-by fixers** (consider adding, or skip):
  Anon Contributor — 1 commit — typo fix in README.md

**Acknowledged in ABOUT only** (also needs README): <list if any>
**Acknowledged in README only** (also needs ABOUT): <list if any>

**Already acknowledged in both** (sanity-check): N contributors covered.
```

End with a one-line **verdict**:

- **Clean** — every substantial contributor is acknowledged in both files.
- **Minor issues** — only drive-by fixers missing, or only single-file drift (acknowledged in one but not the other).
- **Needs attention** — substantial contributors missing.

**CHECKPOINT — pause and ask the user whether to draft acknowledgement additions to `docs/ABOUT.md` and `README.md` (mirrored in both so they stay in sync), or move on.** Do not edit either file without confirmation.

## Final summary

After all five steps complete, give a one-line overall verdict for release readiness — the worst-case verdict across the five checks. List any remaining Critical/Major findings the user needs to address before the `release/X.Y.Z` → `main` merge.

Reminder: this command does not ship the release. Merging `release/X.Y.Z` to `main`, tagging, building the installer, and creating the GitHub release are separate steps documented in root `CLAUDE.md` → *Version & Release → Release checklist*.

---
description: Audit the current branch's source changes for matching test coverage in tests/
---

# /test_coverage_check

For every source file modified on the current branch, decide whether it should have a unit test and whether that test exists or was updated. Surface gaps; don't auto-write tests.

## Severities

- **Critical** — non-exempt code (per the table below) with no matching test. Blocks merge in `/pull_request`.
- **Major** — existing test covers an old branch of changed logic but does not exercise the new branch.
- **Minor** — exempt code (workers, GUI wiring, scripts) flagged for manual attention so the user remembers to smoke-test.

## Scoping the diff

```bash
git diff --name-only $(git merge-base HEAD origin/main)...HEAD
```

If `origin/main` is not the right baseline (e.g. on a `release/X.Y.Z` integration branch), use the integration branch as the base instead.

## Coverage rules

| Area | Coverage requirement |
|---|---|
| `src/utils/`, `src/parser/`, `src/merger/`, `src/models/` | **Required.** New public functions, new classes, changed branching logic need new or updated tests in `tests/`. |
| Pure-Python helpers extracted from GUI: `validate_applied_file`, `filter_entry_indices`, `markdown_to_html` | **Required** — these were specifically extracted so they could be tested without Qt. |
| `src/gui/workers.py` (`QThread` workers) | **Exempt.** Needs `pytest-qt` (not a dev dep). Manual smoke testing is the documented path. Flag for human attention. |
| `src/gui/*.py` (widget layout, signal connections, MainWindow wiring) | **Exempt.** Manual GUI testing only. Surface for review. |
| `scripts/` | **Exempt.** Manual CLI exercise. Surface for review. |

## Procedure

1. Run the diff. Group the file list by area per the table above.
2. For each non-exempt file, identify the new or changed callable (function/class). Check `tests/` for a matching test (filename convention is `test_<module>.py`, function `test_<callable>_<scenario>`).
3. For changed branching logic in existing code, confirm the existing test covers the new branch — read the test to verify, don't trust the filename alone.
4. Run `pytest tests/` and report pass/fail with the count.

## Output

Group findings by severity:

```
**Critical** (non-exempt code without tests):
  src/utils/foo.py::bar  — no matching test in tests/
  src/parser/qux.py::Quxer.validate  — new class, no test_qux.py entry

**Major** (stale tests — changed branches not exercised):
  src/utils/baz.py::compute  — test_baz.py covers OLD branch only; new `if x > 0` path uncovered

**Minor** (exempt — flagged for manual attention):
  src/gui/workers.py — new TurretWorker, needs manual smoke run
  src/gui/main_window.py — new toolbar button, manual exercise needed

pytest tests/: PASS (123 passed, 1 skipped)  |  FAIL — see output above
```

End with a one-line **verdict**:

- **Clean** — no Critical/Major findings and pytest passes.
- **Minor issues** — only Minor findings (manual-test flags); pytest passes.
- **Needs attention** — any Critical/Major findings or pytest failures.

After the verdict, **CHECKPOINT — pause and ask whether to draft tests for the Critical findings, or move on.** Wait for the answer before doing anything else.

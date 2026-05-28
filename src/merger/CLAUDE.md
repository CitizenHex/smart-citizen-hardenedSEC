# src/merger/CLAUDE.md

Source merge engine. See the root `CLAUDE.md` for project context (incl. the *Merge hierarchy* design decision).

## Files

- `ini_merger.py` — merge engine: `merge_sources_by_hierarchy(sources_dict, hierarchy, user_overrides)`. Sources merge in order; user overrides win.

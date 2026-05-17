# Test Path Bootstrap Contract

> version: 1.1 | last_updated: 2026-04-26

## Scope
- Applies to pytest-side import bootstrapping in `tests/path_bootstrap.py`.
- Goal: keep test-time imports deterministic across `pytest` and `python -m pytest`.

## Canonical bootstrap paths
1. `PROJECT_ROOT` (`/repo`)
2. `OPS_LIB_ROOT` (`/repo/scripts/ops`) for legacy `lib.*`
3. `ENGINE_LIB_ROOT` (`/repo/scripts/engine`) for engine script tests
4. `UTILS_LIB_ROOT` (`/repo/scripts/utils`) for utils script tests

> Priority rule: prepend in helper order so the intended test target path stays at index 0.

## Rules
- Use bootstrap helpers:
  - `bootstrap_test_sys_path()`
  - `bootstrap_engine_test_sys_path()`
  - `bootstrap_utils_test_sys_path()`
- Allowed:
  - call an existing helper from `tests/path_bootstrap.py`.
  - add a new helper in `tests/path_bootstrap.py` if a new path domain is required.
- Forbidden:
  - ad-hoc `sys.path.insert(...)` / `sys.path.append(...)` in individual tests when helper coverage exists.
- Helpers must:
  - canonicalize paths before comparison,
  - dedupe equivalent entries,
  - prepend required path(s) to the front.

## Why
- Prevents path-order drift between tests.
- Keeps import behavior stable across invocation modes and environments.

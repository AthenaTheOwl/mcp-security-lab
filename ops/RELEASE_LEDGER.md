# RELEASE_LEDGER

Every commit on main that represents shippable scope lands here with
date, SHA, title, scope, and proof refs.

## Format

```
## YYYY-MM-DD — <sha> <title>

- scope: <one or two sentences>
- proof:
  - <gate or test name> — <where the proof lives>
```

## Entries

## 2026-10-19 — 26363279694041f87550587aa8d032a9536e7c9d correction: scout boundary doc withdrawn

- scope: Corrects the 2026-10-18 entry for 0261caa. The read-only scout doc
  and its README pointer are withdrawn, so that entry's scouting-limits scope
  no longer ships. The offline surface-diff fixture, its conformance mapping,
  and its producer test stay. The conformance gate reads generated reports
  only at `reports/mcp-surface-diff*.json`, not every generated runtime report.
- proof:
  - withdrawal — commit 2636327 deletes `docs-read-only-scout.md` and the
    README paragraph that pointed to it
  - pytest — `.github/workflows/ci.yml` (Tests step); fixture and glob
    coverage tests in `tests/test_surface_report_fixture.py`
  - validate_data_conformance — `.github/workflows/ci.yml`
    (validate_data_conformance step)
  - native governance gates — `.github/workflows/ci.yml` (Voice lint through
    Schema cache freshness steps)
  - live surface drift — `.github/workflows/ci.yml` (Validate registered MCP
    server tool surfaces step); the fixture makes no live claim
  - 2026-10-18 entry — CI run on PR #17 head e1da635 —
    https://github.com/AthenaTheOwl/mcp-security-lab/actions/runs/39195073361

## 2026-10-18 — 0261caad7654894a05e2e0c459a24176c86fe61f scout boundary and offline surface fixture

- scope: Document read-only research scouting limits and bind the offline
  surface-diff fixture to the existing report producer. Validate the synthetic
  example and any generated runtime reports; keep the live registry drift gate.
- proof:
  - pytest — full fresh-default suite, including the producer and schema fixture
  - validate_data_conformance — one committed fixture checked on a clean checkout
  - native governance gates — all pass for the scoped source commit above
  - live surface drift — separate CI registry gate; fixture makes no live claim

## 2026-05-25 — pre-CDCP init MCP Security Lab MVP

- scope: Initial MVP commit. Scan static mcp server configs before runtime.
- proof:
  - pytest — `.github/workflows/ci.yml`
  - voice_lint — `.github/workflows/ci.yml`
  - spec_check — `.github/workflows/ci.yml`

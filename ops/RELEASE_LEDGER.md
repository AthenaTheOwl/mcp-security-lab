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

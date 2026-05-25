# Specs

Active specs:

- `0001-mcp-security-lab`: MVP scope for mcp-security-lab.

## Adding a new spec

1. Reserve the next numeric prefix.
2. Create `specs/NNNN-<slug>/requirements.md` with R-<PREFIX>-NNN entries.
3. Create `specs/NNNN-<slug>/traceability.md` mapping each R-* to evidence and DEC coverage.
4. Add one DEC per R-* under `decisions/` (or list as deferred in `decisions/.spec-check-allowlist.yaml`).
5. Run `python scripts/spec_check.py` and `python scripts/validate_decisions.py`; confirm exit 0.

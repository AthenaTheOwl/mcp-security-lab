# .agents/AGENTS.md

The single contract a coding agent (Claude, Codex, or other) reads
before acting on this repo. Specs name what we build. Decisions name
why. This file names how the agent behaves while building.

## Systems-thinking discipline (per DEC-CDCP-020)

Per DEC-CDCP-020 in athena-site, every substantive DEC + dream
candidate + Run record in this repo SHOULD carry four fields:

- `systems_map`: what underlying mechanism does this expose?
- `transferable_principle`: what generalizes beyond this decision?
- `falsification_test`: what would prove this wrong?
- `adoption_ladder`: `minimum_viable` → `mid_adoption` →
  `full_adoption` plus `monitoring_signals`.

All four fields are optional in the schema. The validator emits a
warning when missing on new DECs. After 30 days, the warning ratchets
to failure via amendment DEC.

## Coding style

- Python 3.11. Install with `python -m pip install -e ".[dev]"`.
- pytest for tests. The `pyproject.toml` pins the toolchain.
- Edit existing files. Use the `Edit` tool over `Write` when the file
  already exists; `Write` rewrites the whole file and risks losing
  context. Reserve `Write` for new files.
- The static scanner never connects to an MCP server. It reads config
  and writes reports. Live probing is out of scope per
  `DEC-MCPSEC-001-config-scan-before-runtime`.
- The injection phrase corpus is the policy source. New phrases land
  in `mcp_security_lab/injection.py` with a test in
  `tests/test_scoring.py`.

## Domain decisions

- Static config scan before runtime. The scanner never launches an
  MCP server; it reads config and reports.
- Policy corpus over LLM judge. Phrase matching is deterministic and
  testable; no vendor key is required to run the gate.
- JSON plus Markdown report shapes. One payload, two artifacts.
- Voice rules in `scripts/voice_lint.py` are not optional for
  governance copy under the documented globs.

## Workflow conventions

- Push to main directly. The repo's CI runs the gates on push; a
  failed gate fails the check.
- Nine python gates run on every push: `spec_check`, `voice_lint`,
  `validate_decisions`, `validate_roles`, `validate_tools`,
  `validate_policies`, `validate_skills`, `validate_dreams`,
  `check_schema_cache_freshness`. Plus pytest with the example scan
  step in `.github/workflows/ci.yml`.
- Every shipped R-* requirement gets at least one DEC-* file before
  the commit reaches main. `spec_check` flags an orphan R-* unless
  the requirement is listed in
  `decisions/.spec-check-allowlist.yaml` as deferred backfill.
- Dream-job outputs are human-gated. No CI job auto-applies a dream
  candidate. The policy
  `.agents/policies/dream-candidates-require-human-approval.yaml`
  encodes the rule.
- A force-push, history rewrite, or rollback gets an entry in
  `ops/RESET_LEDGER.md` in the same push that performs the rewrite.
- A release gets an entry in `ops/RELEASE_LEDGER.md` with date, SHA,
  title, scope, and proof refs.

## Cross-repo links

- The CDCP charter at `../athena-site/ops/control-plane.md` names
  the six artifact types and the cross-repo contracts.
- The schemas at `../athena-site/ops/schemas/` are the source of
  truth for decision, role, tool, policy, skill, dream-output, and
  artifact shapes. This repo references them by URL and keeps cache
  copies under `ops/schemas-cache/` for offline CI.
- The portfolio manifest at
  `../athena-site/ops/portfolio-manifest.yml` lists every product
  repo and which gates each repo runs.

## Where to look

| If you want to | Read |
|---|---|
| understand the what | `specs/0001-mcp-security-lab/requirements.md` |
| understand the why | `decisions/DEC-MCPSEC-*.md` |
| run a static scan | `README.md` |
| audit a release | `ops/RELEASE_LEDGER.md` |
| audit a history rewrite | `ops/RESET_LEDGER.md` |
| register a new role, tool, or policy | `.agents/CATALOG.md` |

## Failure modes the agent watches for

- A new R-* requirement without a DEC: `spec_check` fails. Fix by
  adding the DEC file in the same commit.
- A DEC file out of schema shape: `validate_decisions` fails. Fix
  the front-matter against `ops/schemas-cache/decision.schema.json`.
- A role, tool, or policy out of shape: the matching `validate_*`
  script fails. Fix against the cached schema.
- A voice-lint hit in governance copy: rewrite the line.

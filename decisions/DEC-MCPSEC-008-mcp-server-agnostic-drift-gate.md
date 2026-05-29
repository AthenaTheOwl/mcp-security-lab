---
id: DEC-MCPSEC-008-mcp-server-agnostic-drift-gate
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-MCPSURF-003
date: 2026-05-29
status: approved
reversible: true
amends: DEC-MCPSEC-007-athena-mcp-surface-drift-gate
decision: |
  The MCP surface drift gate parameterizes over a server registry at
  config/mcp_server_registry.yaml. The gate
  (scripts/validate_mcp_surface.py) defaults to gating every enabled
  registry entry; --server-id selects one; --all is explicit. Adding a
  new MCP server to the gate is a one-line registry append, not a code
  change. The athena-site-specific script remains as a thin alias.
alternatives:
  - label: keep hardcoding athena-site, copy-paste the gate per new server
    rejected_because: |
      The next MCP server (Codex's planned runtime surface, third-party
      SDK MCP servers) would each need its own script, its own CI step,
      and its own snapshot path threaded through workflow YAML. Drift
      detection that requires copy-paste per server stops being run for
      servers no one wants to touch.
  - label: discover MCP servers by directory convention
    rejected_because: |
      Convention-based discovery couples the lab to a specific repo
      layout the lab does not control. The registry is an explicit
      contract: someone added this server, on purpose, with this
      snapshot-script command. That signal is what the gate is for.
  - label: have each server repo run its own drift gate locally
    rejected_because: |
      Per-repo gates duplicate snapshot tooling and lose the single
      pane the lab provides for portfolio-wide MCP risk. The lab
      already owns the policy corpus, the scoring rules, and the
      per-server reports; routing surface drift through the same
      pipeline lets reviewers see one report shape across servers.
rationale: |
  DEC-MCPSEC-007 commits the lab to gating athena-site's MCP server
  tool surface against drift. The narrow scope was correct for round
  1: prove the contract, prove the binary-I/O fix, prove the CI seam.
  But the lab's job is portfolio-wide MCP security, not one server's
  security. Codex will publish a runtime MCP server next; third-party
  SDK servers will land after that. Each one needs the same
  drift-detection treatment.

  The registry is the unit of extension. A YAML file lists the servers
  the lab cares about; the gate iterates that list; CI runs --all and
  exits 1 if any server drifts. The shape of the gate, the shape of
  the report, the shape of the test fixtures — all stay constant as
  the registry grows. Round 1's binary-I/O snapshot restore lives on
  inside the per-server loop; the discipline that DEC-MCPSEC-007
  earned is preserved, not rewritten.

  The legacy script and the ATHENA_SITE_REPO env var still work. The
  registry maps id "athena-portfolio-query" to that env name via an
  alias table so anyone with existing CI invocations does not break.
  When the next server lands, it gets its own
  <ID_UPPER>_REPO / <ID_UPPER>_LIVE_SNAPSHOT pair, declared by the
  same registry entry.
evidence:
  - kind: code
    ref: scripts/validate_mcp_surface.py
  - kind: code
    ref: scripts/validate_athena_mcp_surface.py
  - kind: config
    ref: config/mcp_server_registry.yaml
  - kind: schema
    ref: schemas/mcp-surface-diff.schema.json
  - kind: test
    ref: tests/test_validate_mcp_surface_registry.py
  - kind: test
    ref: tests/test_validate_athena_mcp_surface.py
  - kind: decision
    ref: decisions/DEC-MCPSEC-007-athena-mcp-surface-drift-gate.md
rollback: |
  Revert this DEC's commits: drop config/mcp_server_registry.yaml,
  drop scripts/validate_mcp_surface.py, drop
  tests/test_validate_mcp_surface_registry.py, restore the prior
  contents of scripts/validate_athena_mcp_surface.py and the CI step
  that called it. DEC-MCPSEC-007's single-server gate continues to
  work because nothing about that path has been deleted — the alias
  preserves the old CLI shape end-to-end.
owner: platform
systems_map: |
  Registry-as-extension-unit for portfolio-wide gates. The lab owns
  one gate, one report shape, one test fixture pattern; a YAML
  registry lists which servers the gate iterates. Per-server scripts
  would scale the gate's complexity with the portfolio; the registry
  keeps complexity flat regardless of how many MCP servers join.
transferable_principle: |
  When a single-target gate proves itself, parameterize over a
  registry before the second target lands — the registry shape is
  cheaper to design once than to retrofit after copy-paste duplication
  has set in.
falsification_test: |
  If adding the second registered MCP server (e.g. Codex's runtime
  surface) requires more than a one-line registry append plus
  per-server env-var declaration, the registry-as-unit-of-extension
  claim is falsified and the gate needs another redesign pass.
adoption_ladder:
  minimum_viable: |
    Registry parses; --server-id targets one server; legacy alias
    script keeps DEC-MCPSEC-007 CLI working.
  mid_adoption: |
    CI runs --all by default; second MCP server joins via registry
    append; per-server diff reports land at deterministic paths.
  full_adoption: |
    Every portfolio MCP server is registered; disabled-flag handles
    deprecation; the alias script can be removed once no CI invocation
    uses it.
  monitoring_signals:
    - registry entry count over time
    - per-server drift_detected rate per gate run
    - count of CI invocations still using the legacy alias script
---

## decision

The MCP surface drift gate parameterizes over a server registry at
`config/mcp_server_registry.yaml`. The gate
(`scripts/validate_mcp_surface.py`) defaults to gating every enabled
registry entry; `--server-id` selects one; `--all` is explicit. Adding
a new MCP server to the gate is a one-line registry append, not a
code change. The athena-site-specific script remains as a thin alias
so DEC-MCPSEC-007's CLI contract keeps working.

## alternatives

- Keep hardcoding athena-site, copy-paste the gate per new server.
  Rejected: per-server scripts and per-server CI steps mean drift
  detection stops being run on the servers no one wants to touch.
- Discover MCP servers by directory convention. Rejected: convention
  couples the lab to a repo layout the lab does not control. The
  registry is an explicit contract.
- Have each server repo run its own drift gate locally. Rejected:
  duplicates tooling and loses the single pane the lab provides for
  portfolio-wide MCP risk reporting.

## rationale

DEC-MCPSEC-007 committed the lab to gating athena-site's MCP server
tool surface against drift. Round 1's narrow scope was correct: prove
the contract, prove the binary-I/O fix, prove the CI seam. But the
lab's job is portfolio-wide MCP security, not one server's security.
Codex will publish a runtime MCP server next; third-party SDK servers
will land after that. Each one needs the same drift-detection
treatment.

The registry is the unit of extension. A YAML file lists the servers
the lab cares about; the gate iterates that list; CI runs `--all` and
exits 1 if any server drifts. The shape of the gate, the shape of the
report, the shape of the test fixtures stay constant as the registry
grows. Round 1's binary-I/O snapshot restore lives on inside the
per-server loop; the discipline DEC-MCPSEC-007 earned is preserved,
not rewritten.

The legacy script and the `ATHENA_SITE_REPO` env var still work. The
registry maps id `athena-portfolio-query` to that env name via an
alias table so existing CI invocations do not break. When the next
server lands, it gets its own `<ID_UPPER>_REPO` /
`<ID_UPPER>_LIVE_SNAPSHOT` pair, declared by the same registry entry.

## evidence

- `scripts/validate_mcp_surface.py` — the parameterized gate.
- `scripts/validate_athena_mcp_surface.py` — the back-compat alias.
- `config/mcp_server_registry.yaml` — the registry of gated servers.
- `schemas/mcp-surface-diff.schema.json` — diff-report schema (unchanged from DEC-MCPSEC-007).
- `tests/test_validate_mcp_surface_registry.py` — registry parsing,
  multi-server gate, disabled-server skip, exit-code aggregation.
- `tests/test_validate_athena_mcp_surface.py` — single-server CLI
  contract regression coverage.
- `decisions/DEC-MCPSEC-007-athena-mcp-surface-drift-gate.md` — the
  amended prior DEC.

## requirement coverage

This DEC resolves three new requirements that extend R-MCPSEC-MCPSURF-001/002:
R-MCPSEC-MCPSURF-003 (registry-parameterized drift gate),
R-MCPSEC-MCPSURF-004 (default-all CI behaviour with per-server diff
reports), and R-MCPSEC-MCPSURF-005 (registry validation: malformed
YAML, missing required fields, duplicate ids, and disabled-entry
skip). All three land in `specs/0001-mcp-security-lab/requirements.md`
alongside this DEC.

## rollback

Revert this DEC's commits: drop
`config/mcp_server_registry.yaml`, drop
`scripts/validate_mcp_surface.py`, drop
`tests/test_validate_mcp_surface_registry.py`, restore the prior
contents of `scripts/validate_athena_mcp_surface.py` and the CI step
that called it. DEC-MCPSEC-007's single-server gate continues to
work because nothing about that path has been deleted — the alias
preserves the old CLI shape end-to-end.

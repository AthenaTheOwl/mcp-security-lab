---
id: DEC-MCPSEC-007-athena-mcp-surface-drift-gate
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-MCPSURF-001
date: 2026-05-27
status: approved
reversible: true
decision: |
  mcp-security-lab gates against drift in athena-site MCP server's
  public tool surface. The gate (scripts/validate_athena_mcp_surface.py)
  reads the committed apps/mcp-server/tool-surface.snapshot.json from
  the sibling athena-site repo, regenerates the live surface via the
  same snapshot script, and exits 1 if the two diverge on any tool
  name, description, or input-schema hash. The structured diff report
  conforms to schemas/mcp-surface-diff.schema.json.
alternatives:
  - label: parse the TypeScript tool sources directly
    rejected_because: |
      A bespoke TypeScript parser would have to track every refactor in
      apps/mcp-server/src/tools/*.ts and would drift from what the
      server actually publishes via tools/list. Regenerating the
      snapshot via the same script the server commits guarantees the
      gate sees exactly what an MCP client would see.
  - label: connect to the live server over stdio and call tools/list
    rejected_because: |
      Starting the server inside this gate adds a process-lifecycle
      dependency (kill on timeout, parse stderr, transport quirks on
      Windows). The snapshot script is deterministic and reproducible;
      the gate runs the snapshot in seconds and gets a structured
      result without any IPC.
  - label: hash the whole apps/mcp-server/src/ tree
    rejected_because: |
      A tree hash fails CI on every internal refactor, including
      changes that do not affect the public surface (private helper
      rename, comment edits). The contract is the surface, not the
      implementation.
rationale: |
  The Phase E thesis is that the portfolio's authoritative model
  becomes useful only when other agents can query it through a stable
  contract. The athena-site MCP server is that contract. A contract
  without drift detection is not a contract — it is a wish.

  Surface drift is silent capability change for every downstream
  agent. Today a tool means one thing; tomorrow a refactor changes
  its input shape and every prompt against it starts producing the
  wrong output. mcp-security-lab already specializes in MCP server
  scanning (DEC-MCPSEC-001, DEC-MCPSEC-006); adding the athena-site
  surface gate fits that mission without expanding scope.

  The gate uses the snapshot script as the live source so the gate's
  view of "live" is exactly what the server commits when it
  regenerates. The committed snapshot is the contract; drift means
  the snapshot was not regenerated when it should have been, which
  is the exact moment a reviewer needs to look at the change.
evidence:
  - kind: code
    ref: scripts/validate_athena_mcp_surface.py
  - kind: schema
    ref: schemas/mcp-surface-diff.schema.json
  - kind: test
    ref: tests/test_validate_athena_mcp_surface.py
  - kind: decision
    ref: ../athena-site/decisions/DEC-CDCP-012-athena-mcp-server-exposes-portfolio-model.md
  - kind: schema
    ref: ../athena-site/apps/mcp-server/src/schemas/tool-surface.json
  - kind: schema
    ref: ../athena-site/apps/mcp-server/tool-surface.snapshot.json
rollback: |
  Remove scripts/validate_athena_mcp_surface.py, the schemas/
  mcp-surface-diff.schema.json file, the test file, and the
  validate_athena_mcp_surface CI step. The other gates and the diff
  CLI continue to function because this gate is independent. The
  athena-site MCP server continues to operate; only the drift gate is
  removed.
owner: platform
systems_map: |
  Contract-via-committed-snapshot for cross-repo APIs. The MCP
  server's tool surface is a stable contract; the snapshot file is
  the contract artifact; regenerating the snapshot via the server's
  own script gives the gate the same view a real MCP client gets.
  Drift means the snapshot was not regenerated when it should have
  been, which is exactly the moment a reviewer needs to look.
transferable_principle: |
  A contract without drift detection is a wish; ship the gate the
  same week the contract artifact lands, using the contract producer's
  own regeneration script as the live source so producer and gate
  cannot diverge in interpretation.
falsification_test: |
  If a downstream agent breaks against the athena-site MCP server
  surface while the gate reports drift_detected: false on the same
  commit range, the snapshot-as-contract claim is falsified and the
  gate is missing a surface dimension (e.g. output schema, error
  envelope, tool ordering) the contract should cover.
adoption_ladder:
  minimum_viable: |
    Gate compares committed snapshot to live regeneration for the
    athena-site MCP server; exits 1 on any tool name, description, or
    input-schema hash divergence; emits a structured diff report.
  mid_adoption: |
    Diff report shape locked behind a schema; tests cover match,
    drift, missing-snapshot, malformed-snapshot, and real-snapshot
    cases; CI runs the gate on every push.
  full_adoption: |
    Gate generalizes via DEC-MCPSEC-008's registry so additional MCP
    servers enroll without code changes; per-server diff reports feed
    a single portfolio dashboard.
  monitoring_signals:
    - drift_detected rate per gate run on main
    - count of malformed-snapshot failures (signals snapshot tooling
      drift)
    - time-to-merge for PRs that touch the snapshot
---

## decision

mcp-security-lab gates against drift in athena-site MCP server's
public tool surface. The gate
(`scripts/validate_athena_mcp_surface.py`) reads the committed
`apps/mcp-server/tool-surface.snapshot.json` from the sibling
athena-site repo, regenerates the live surface, and exits 1 if the
two diverge on any tool name, description, or input-schema hash. The
structured diff report conforms to
`schemas/mcp-surface-diff.schema.json`.

## alternatives

- Parse the TypeScript tool sources directly. Rejected: a bespoke
  parser would drift from what the server publishes via `tools/list`.
  Regenerating the snapshot via the same script the server commits
  guarantees the gate sees exactly what an MCP client would see.
- Connect to the live server over stdio. Rejected: process-lifecycle
  dependency adds IPC noise the snapshot script avoids.
- Hash the whole `apps/mcp-server/src/` tree. Rejected: a tree hash
  fails CI on every internal refactor including ones that do not
  change the public surface.

## rationale

Surface drift is silent capability change for every downstream agent.
The Phase E thesis is that the portfolio's authoritative model
becomes useful only when other agents can query it through a stable
contract; a contract without drift detection is a wish. mcp-security-
lab already specializes in MCP server scanning (DEC-MCPSEC-001,
DEC-MCPSEC-006); adding the athena-site surface gate fits that
mission without expanding scope.

The gate uses the snapshot script as the live source so the gate's
view of "live" is exactly what the server commits when it regenerates.
The committed snapshot is the contract; drift means the snapshot was
not regenerated when it should have been, which is the exact moment
a reviewer needs to look at the change.

## evidence

- `scripts/validate_athena_mcp_surface.py` — the gate script.
- `schemas/mcp-surface-diff.schema.json` — diff-report schema.
- `tests/test_validate_athena_mcp_surface.py` — match, drift, missing-
  snapshot, malformed-snapshot, real-snapshot, and report-schema
  conformance tests.
- `../athena-site/decisions/DEC-CDCP-012-athena-mcp-server-exposes-portfolio-model.md`
  — the upstream DEC that commits the MCP server.
- `../athena-site/apps/mcp-server/src/schemas/tool-surface.json` and
  `../athena-site/apps/mcp-server/tool-surface.snapshot.json` — the
  schema and the source-of-truth snapshot the gate reads.

## requirement coverage

This DEC resolves the new requirement R-MCPSEC-MCPSURF-001 (drift
gate over athena-site MCP server tool surface) and a companion
R-MCPSEC-MCPSURF-002 (structured diff report). Both land in
`specs/0001-mcp-security-lab/requirements.md` alongside this DEC.

## rollback

Remove `scripts/validate_athena_mcp_surface.py`,
`schemas/mcp-surface-diff.schema.json`,
`tests/test_validate_athena_mcp_surface.py`, and the
`validate_athena_mcp_surface` CI step. The other gates and the diff
CLI continue to function because this gate is independent. The
athena-site MCP server continues to operate; only the drift gate is
removed.

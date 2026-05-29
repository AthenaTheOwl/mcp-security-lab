---
id: DEC-MCPSEC-006-baseline-current-diff-gate
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-DIFF-001
date: 2026-05-25
status: approved
reversible: true
decision: |
  MCP Security Lab treats baseline-versus-current report comparison
  as the config diff gate boundary. The gate consumes two existing
  JSON scan reports, computes a deterministic diff, and fails only
  when a requested fail flag matches a net-new high or critical risk
  or a new policy deny decision.
alternatives:
  - label: diff raw MCP config files
    rejected_because: |
      Raw config diffs would miss scoring and policy context. The
      gate would need to re-run the scanner and policy evaluator,
      which makes the boundary less clear for CI.
  - label: fail on any report change
    rejected_because: |
      Any-change failure blocks safe edits such as removing findings,
      lowering risk, or changing comments in generated report paths.
      CI needs to block new unsafe state, not every report delta.
  - label: compare only aggregate summary counts
    rejected_because: |
      Aggregate counts can hide a new deny decision behind a removed
      one. Server and tool keyed comparison keeps the failure tied to
      the exact new signal.
rationale: |
  Existing scan reports already contain the stable security signals:
  risk levels, finding IDs, severities, and policy verdicts. Using
  those reports as inputs keeps the gate deterministic and makes the
  CI artifact reviewable without external services or live MCP
  startup.
evidence:
  - kind: spec
    ref: specs/0001-mcp-security-lab/requirements.md
  - kind: spec
    ref: specs/0001-mcp-security-lab/traceability.md
  - kind: decision
    ref: decisions/DEC-MCPSEC-003-json-and-markdown-report-shapes.md
  - kind: decision
    ref: decisions/DEC-MCPSEC-005-policy-evaluation-over-score-only-warnings.md
rollback: |
  Remove the diff CLI command, the diff module, and the diff fixture
  tests. Existing scan and policy gates continue to work because the
  diff gate reads their JSON output and does not alter report
  generation.
owner: platform
systems_map: |
  Reports-as-stable-interface for CI gates. The scanner emits a
  typed JSON report; the diff gate consumes two reports and produces
  a structured comparison without re-running the scanner. Putting
  the gate at the report boundary lets scoring and policy logic
  evolve independently of the diff logic.
transferable_principle: |
  When a pipeline emits a typed artifact, build downstream gates on
  the artifact, not on the pipeline's internals — the gate stays
  stable across producer refactors and the artifact stays the
  reviewable evidence.
falsification_test: |
  If a config change that introduces a net-new high-risk finding
  fails to flip the gate to exit 1 with --fail-on-high (or vice
  versa: a benign report edit triggers a false fail), the
  baseline-vs-current comparison is missing a signal the report
  shape claims to encode.
adoption_ladder:
  minimum_viable: |
    Diff CLI consumes two scan reports, classifies added/removed/
    changed findings, and exits 0 unconditionally.
  mid_adoption: |
    --fail-on-high and --fail-on-deny flags wire CI to specific
    risk-class deltas; fixtures cover added/removed/changed per
    server and per tool.
  full_adoption: |
    Diff reports feed the portfolio dashboard alongside the surface
    drift gate (DEC-MCPSEC-007/008); a single review packet shows
    config drift, surface drift, and policy verdict drift together.
  monitoring_signals:
    - rate of --fail-on-* gate failures per week
    - count of net-new high/critical risks introduced per merged PR
    - false-positive reports filed against the diff CLI
---

## decision

MCP Security Lab treats baseline-versus-current report comparison as
the config diff gate boundary. The gate consumes two existing JSON
scan reports and computes a deterministic diff.

## alternatives

- Diff raw MCP config files. Rejected because raw config lacks the
  scoring and policy verdict context needed for the gate.
- Fail on any report change. Rejected because safe edits such as
  removed findings should not block CI.
- Compare only aggregate summary counts. Rejected because counts can
  hide a new deny decision behind a removed one.

## rationale

Existing scan reports already carry the security signals this gate
needs: risk levels, finding IDs, severities, and policy verdicts.
Using them as inputs keeps the gate deterministic and reviewable.

## evidence

- `specs/0001-mcp-security-lab/requirements.md`
- `specs/0001-mcp-security-lab/traceability.md`
- `decisions/DEC-MCPSEC-003-json-and-markdown-report-shapes.md`
- `decisions/DEC-MCPSEC-005-policy-evaluation-over-score-only-warnings.md`

## rollback

Remove the diff CLI command, the diff module, and the diff fixture
tests. Existing scan and policy gates continue to work because the
diff gate reads their JSON output and does not alter report
generation.

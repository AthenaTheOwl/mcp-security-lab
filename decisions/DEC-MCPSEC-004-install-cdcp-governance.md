---
id: DEC-MCPSEC-004-install-cdcp-governance
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-005
date: 2026-05-25
status: approved
reversible: true
decision: |
  Install the Cognitive Delivery Control Plane governance scaffold
  in `mcp-security-lab` to match the portfolio baseline. The pass
  adds `.agents/` (AGENTS.md, CATALOG.md, six role contracts, tool
  registry, policy files, state machines, workflows), `dreams/`,
  `ops/` (RELEASE_LEDGER, RESET_LEDGER, event-log, schemas-cache),
  decision-index files under `decisions/`, and seven new gate scripts
  under `scripts/` (`validate_decisions`, `validate_roles`,
  `validate_tools`, `validate_policies`, `validate_skills`,
  `validate_dreams`, `check_schema_cache_freshness`).
alternatives:
  - label: stay on CDCP-lite (specs + DECs + voice_lint + spec_check)
    rejected_because: |
      CDCP-lite carries no executable shape check on DECs, roles,
      tools, or policies. The trust-face repo benefits most from
      schema-gated discipline. The other product repos already run
      the full set; matching the baseline keeps the portfolio audit
      story one shape.
  - label: defer the install until artifact volume forces it
    rejected_because: |
      Backfilling later means the early commits get no schema-shaped
      DEC and the trail has a gap. Installing now keeps the records
      consistent from the start.
rationale: |
  This repo is the "trust face" of the agent factory. It documents
  how MCP servers are reviewed before they run. The discipline shown
  in this repo's own scaffolding is part of the trust claim. The
  same gate scripts that catch DEC shape drift in
  `supplier-risk-rag-agent` and `ai-field-brief` now run here.
evidence:
  - kind: spec
    ref: specs/0001-mcp-security-lab/requirements.md
  - kind: decision
    ref: ../supplier-risk-rag-agent/decisions/DEC-CDCP-001-install-cdcp-governance.md
  - kind: doc
    ref: ../athena-site/ops/control-plane.md
  - kind: doc
    ref: ops/schemas-cache/decision.schema.json
rollback: |
  Revert this commit. The added directories (`.agents/`, `dreams/`,
  `ops/`) and the seven new gate scripts under `scripts/` can be
  removed wholesale. The product code under `mcp_security_lab/` and
  the existing CI workflow continue to function with only
  `spec_check` and `voice_lint`. The three pre-install DECs reverted
  to the lite shape can carry the front-matter rewrite forward; no
  data loss.
owner: platform
---

## decision

Install the Cognitive Delivery Control Plane governance scaffold in
`mcp-security-lab` to match the portfolio baseline. The pass adds
`.agents/`, `dreams/`, `ops/`, decision-index files, and seven new
gate scripts under `scripts/`.

## alternatives

- Stay on CDCP-lite (specs + DECs + voice_lint + spec_check).
  Rejected because the trust-face repo benefits most from
  schema-gated discipline.
- Defer the install until artifact volume forces it. Rejected
  because backfilling later leaves a gap in the early commits.

## rationale

This repo is the trust face of the agent factory. The discipline
shown in the scaffolding is part of the trust claim. The same gate
scripts that catch DEC shape drift in `supplier-risk-rag-agent` and
`ai-field-brief` now run here.

## evidence

- `specs/0001-mcp-security-lab/requirements.md`
- `../supplier-risk-rag-agent/decisions/DEC-CDCP-001-install-cdcp-governance.md`
- `../athena-site/ops/control-plane.md`
- `ops/schemas-cache/decision.schema.json`

## rollback

Revert this commit. The added directories and gate scripts can be
removed wholesale. The product code and the existing CI workflow
continue to function with only `spec_check` and `voice_lint`.

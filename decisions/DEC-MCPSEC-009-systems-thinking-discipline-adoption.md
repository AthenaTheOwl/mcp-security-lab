---
id: DEC-MCPSEC-009-systems-thinking-discipline-adoption
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-010
date: 2026-05-29
status: approved
reversible: true
amends: DEC-MCPSEC-008-mcp-server-agnostic-drift-gate
decision: |
  mcp-security-lab adopts DEC-CDCP-020's systems-thinking discipline.
  The schema cache under `ops/schemas-cache/` mirrors athena-site's
  amended `decision.schema.json`, `dream-output.schema.json`, and
  `run.schema.json`, all of which now carry the four optional fields
  `systems_map`, `transferable_principle`, `falsification_test`, and
  `adoption_ladder`. `.agents/AGENTS.md` names the discipline so
  agents landing changes in this repo know the contract.
  `scripts/validate_decisions.py` emits a stderr warning when an
  approved DEC misses any of the four fields; exit code stays 0
  during the 30-day bootstrap window. DEC-MCPSEC-006/007/008 carry
  retrofitted fields as a demonstration.
alternatives:
  - label: wait for athena-site to ratchet the fields to required, then adopt
    rejected_because: |
      Portfolio-wide alignment means landing the same shape in every
      product repo on the same week. Waiting lets the schemas in the
      offline cache drift away from athena-site's, which silently
      breaks the gate any time the cache is reused without a manual
      refresh. Adopting now keeps the cache and the discipline in
      lockstep with the source of truth.
  - label: adopt the fields but skip the validator warning
    rejected_because: |
      An adopted contract without an enforcement signal is a
      preference, not a discipline. The stderr warning is the
      cheapest signal that still tells a reviewer "this DEC is
      missing the four fields"; without it, new DECs land empty and
      the discipline does not take hold.
  - label: retrofit every historical DEC in one pass
    rejected_because: |
      DEC-MCPSEC-001 through 005 predate the discipline and carry
      contexts the authors no longer remember in full. A three-DEC
      demonstration (006/007/008, the active gates) is enough to
      prove the field shape works; the rest can land as the
      discipline ratchets to failure or as the related code is
      revisited.
rationale: |
  DEC-CDCP-020 in athena-site amended three schemas to carry four
  optional fields. The discipline lands in mcp-security-lab via four
  moves: refresh the cache (so the offline CI sees the same schema as
  the source of truth), name the contract in AGENTS.md (so the next
  agent landing a DEC knows what to populate), extend the validator
  (so missing fields generate a reviewable signal), and retrofit the
  three most-recent DECs (so the field shape is demonstrated, not
  hypothetical).

  The pattern of (cache → AGENTS.md → validator → retrofit) is itself
  the transferable principle: any future cross-repo schema discipline
  lands the same way, regardless of which fields the schema gains.
evidence:
  - kind: schema
    ref: ops/schemas-cache/decision.schema.json
  - kind: schema
    ref: ops/schemas-cache/dream-output.schema.json
  - kind: schema
    ref: ops/schemas-cache/run.schema.json
  - kind: code
    ref: scripts/validate_decisions.py
  - kind: doc
    ref: .agents/AGENTS.md
  - kind: decision
    ref: ../athena-site/decisions/DEC-CDCP-020-systems-thinking-discipline-four-fields.md
  - kind: decision
    ref: decisions/DEC-MCPSEC-006-baseline-current-diff-gate.md
  - kind: decision
    ref: decisions/DEC-MCPSEC-007-athena-mcp-surface-drift-gate.md
  - kind: decision
    ref: decisions/DEC-MCPSEC-008-mcp-server-agnostic-drift-gate.md
rollback: |
  Revert this DEC's commits: drop the four new R-MCPSEC-010..013 rows
  from `specs/0001-mcp-security-lab/requirements.md` and
  `traceability.md`, drop the systems-thinking section in
  `.agents/AGENTS.md`, drop `check_systems_thinking_fields` and the
  warning block from `scripts/validate_decisions.py`, restore the
  prior contents of the three retrofitted DECs, and restore the
  prior cached schemas. The other gates continue to function because
  the four new fields stay optional in the schema; rolling back this
  DEC removes the per-repo adoption signal without breaking
  validation.
owner: security.threat-modeler
systems_map: |
  Per-repo adoption of a cross-repo control-plane discipline. The
  schema cache is the contract, AGENTS.md is the readme, the
  validator is the enforcement, and the retrofit is the
  demonstration. Each move is independently reversible; together
  they ratchet the discipline into the repo.
transferable_principle: |
  Any cross-repo schema discipline lands via (cache → AGENTS.md →
  validator → retrofit) — the same pattern applies to future
  portfolio-wide schema amendments regardless of the field set.
falsification_test: |
  If new DECs in this repo over the next 30 days populate the four
  fields at under 20 percent rate despite the validator warning, the
  discipline is not taking hold and the adoption pattern needs
  escalation (mandatory-ratchet DEC sooner, or a different signal
  than stderr warnings).
adoption_ladder:
  minimum_viable: |
    Schema cache refreshed; validator emits stderr warnings on
    approved DECs missing any of the four fields.
  mid_adoption: |
    AGENTS.md names the contract; new DECs land with the four fields
    populated organically; the validator's warning list shrinks per
    week.
  full_adoption: |
    Validator fails (exit 1) on missing fields per a follow-up
    amendment DEC; at least 80 percent of historical DECs are
    retrofitted; the discipline applies equally to dream candidates
    and Run records via the parallel schemas.
  monitoring_signals:
    - new-DEC field-population rate per week
    - validator warning count trend over time
    - count of dream candidates and Run records carrying the four
      fields
---

## decision

mcp-security-lab adopts DEC-CDCP-020's systems-thinking discipline.
The schema cache under `ops/schemas-cache/` mirrors athena-site's
amended schemas. `.agents/AGENTS.md` names the discipline.
`scripts/validate_decisions.py` emits a stderr warning when an
approved DEC misses any of the four fields. DEC-MCPSEC-006/007/008
carry retrofitted fields.

## alternatives

- Wait for athena-site to ratchet the fields to required before
  adopting. Rejected: portfolio-wide alignment means landing the
  same shape on the same week; waiting lets the offline cache drift
  away from athena-site.
- Adopt the fields but skip the validator warning. Rejected: an
  adopted contract without an enforcement signal is a preference,
  not a discipline.
- Retrofit every historical DEC in one pass. Rejected: DEC-MCPSEC-001
  through 005 predate the discipline; a three-DEC demonstration is
  enough to prove the shape works.

## rationale

DEC-CDCP-020 amended three schemas to carry four optional fields.
The discipline lands here via four moves: refresh the cache, name
the contract in AGENTS.md, extend the validator, retrofit the three
most-recent DECs. The pattern of (cache → AGENTS.md → validator →
retrofit) is the transferable principle.

## evidence

- `ops/schemas-cache/decision.schema.json` — mirrored schema with
  four new optional fields.
- `ops/schemas-cache/dream-output.schema.json` — same fields for
  dream candidates.
- `ops/schemas-cache/run.schema.json` — same fields for Run records.
- `scripts/validate_decisions.py` — `check_systems_thinking_fields`
  emits stderr warnings.
- `.agents/AGENTS.md` — Systems-thinking discipline section.
- `../athena-site/decisions/DEC-CDCP-020-*.md` — the upstream DEC.
- `decisions/DEC-MCPSEC-006/007/008-*.md` — the retrofitted DECs.

## requirement coverage

This DEC resolves four new requirements: R-MCPSEC-010 (schema-cache
refresh), R-MCPSEC-011 (AGENTS.md contract), R-MCPSEC-012 (validator
warning), and R-MCPSEC-013 (three-DEC retrofit). All four land in
`specs/0001-mcp-security-lab/requirements.md` alongside this DEC.

## rollback

Revert this DEC's commits: drop the four R-MCPSEC-010..013 rows from
the spec ledger, drop the systems-thinking section in AGENTS.md,
drop `check_systems_thinking_fields` from
`scripts/validate_decisions.py`, restore the prior contents of the
three retrofitted DECs, and restore the prior cached schemas. The
other gates continue to function because the four fields stay
optional in the schema.

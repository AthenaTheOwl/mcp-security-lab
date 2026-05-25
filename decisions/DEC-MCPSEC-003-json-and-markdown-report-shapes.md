---
id: DEC-MCPSEC-003-json-and-markdown-report-shapes
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-004
date: 2026-05-25
status: approved
reversible: true
decision: |
  Every scan builds one internal report payload and writes two
  artifacts: a JSON file for machines and a Markdown file for
  reviewers. The CLI exposes one `--out` path for JSON and a paired
  `--markdown` path; the default Markdown path is the JSON path with
  the suffix swapped to `.md`.
alternatives:
  - label: JSON only, render Markdown out of band
    rejected_because: |
      Out-of-band rendering forces every downstream user (CI bot,
      reviewer, archive) to re-implement the same renderer. Two
      artifacts from one payload keeps the rendering rule in one
      place.
  - label: Markdown only, drop JSON
    rejected_because: |
      A machine-readable shape is needed for CI diffs, report
      archival, and downstream tooling. Markdown only is a worse fit
      for diff review.
  - label: PDF or HTML report
    rejected_because: |
      Premature. Markdown plus JSON cover the first audience.
rationale: |
  One payload, two artifacts is the cheapest contract that serves
  both audiences. JSON is diffable in CI; Markdown is reviewable in
  pull requests, issue comments, and archived evidence. The CLI
  stays simple and the test surface stays narrow.
evidence:
  - kind: spec
    ref: specs/0001-mcp-security-lab/requirements.md
  - kind: spec
    ref: specs/0001-mcp-security-lab/traceability.md
rollback: |
  Remove the Markdown renderer and emit JSON only. The internal
  report payload stays the same; only the artifact set narrows. No
  downstream tooling depends on the Markdown shape yet, so the
  rollback path is a one-file revert.
owner: platform
---

## decision

Every scan builds one internal report payload and writes two
artifacts: a JSON file for machines and a Markdown file for reviewers.

## alternatives

- JSON only, render Markdown out of band. Rejected because each
  downstream user would re-implement the same renderer.
- Markdown only, drop JSON. Rejected because CI needs a diffable
  shape.
- PDF or HTML. Rejected as premature.

## rationale

One payload, two artifacts is the cheapest contract that serves both
audiences. JSON is diffable in CI; Markdown is reviewable in pull
requests, issue comments, and archived evidence.

## evidence

- `specs/0001-mcp-security-lab/requirements.md`
- `specs/0001-mcp-security-lab/traceability.md`

## rollback

Remove the Markdown renderer and emit JSON only. The internal report
payload stays the same; only the artifact set narrows. No downstream
tooling depends on the Markdown shape yet.

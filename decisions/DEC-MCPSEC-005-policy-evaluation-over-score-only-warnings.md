---
id: DEC-MCPSEC-005-policy-evaluation-over-score-only-warnings
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-POL-001
date: 2026-05-25
status: approved
reversible: true
decision: |
  MCP Security Lab now treats score findings as policy inputs. A
  YAML policy maps finding IDs and tool descriptor text to allow,
  deny, or human_approval_required verdicts in the same JSON and
  Markdown report payload.
alternatives:
  - label: keep score-only warnings
    rejected_because: |
      A score helps triage but does not give CI or reviewers a clear
      action. The Wave 1 policy gate needs a deterministic verdict
      that can fail a command.
  - label: hard-code verdicts in the scanner
    rejected_because: |
      Hard-coded verdicts would force product policy changes into
      scanner code. YAML keeps the enforcement rule reviewable
      without changing the scoring rules.
  - label: call an LLM judge for policy decisions
    rejected_because: |
      The first enforcement layer must be deterministic, cheap to
      test, and suitable for CI. LLM review can be a later advisory
      layer, not the source of the exit code.
rationale: |
  Findings already capture the stable static signals: local command
  startup, broad filesystem access, unauthenticated remote transport,
  injection language, and read-only resources. A YAML policy keeps
  those signals separate from the enforcement choice, so one scanner
  can support permissive local review and stricter CI gates.
evidence:
  - kind: spec
    ref: specs/0001-mcp-security-lab/requirements.md
  - kind: spec
    ref: specs/0001-mcp-security-lab/traceability.md
  - kind: test
    ref: tests/test_policy.py
rollback: |
  Remove the policy CLI flags, policy evaluator module, policy report
  section, and policy fixture tests. The score report remains usable
  because the existing scoring functions do not depend on policy
  evaluation.
owner: platform
---

## decision

MCP Security Lab evaluates a YAML policy after scoring each server.
The policy maps finding IDs and tool descriptor text to allow, deny,
or human_approval_required verdicts.

## alternatives

- Keep score-only warnings. Rejected because CI needs an action, not
  only a numeric signal.
- Hard-code verdicts in scanner code. Rejected because policy changes
  should be reviewable as config.
- Call an LLM judge. Rejected because this gate needs deterministic
  output and an exit code.

## rationale

The scanner should keep finding detection separate from enforcement.
Findings name what was observed; policy names what the organization
does with that observation.

## evidence

- `specs/0001-mcp-security-lab/requirements.md`
- `specs/0001-mcp-security-lab/traceability.md`
- `tests/test_policy.py`

## rollback

Remove the policy CLI flags, policy evaluator module, policy report
section, and policy fixture tests. Existing score reports continue to
work without the policy layer.

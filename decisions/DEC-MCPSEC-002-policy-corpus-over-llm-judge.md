---
id: DEC-MCPSEC-002-policy-corpus-over-llm-judge
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-003
date: 2026-05-25
status: approved
reversible: true
decision: |
  Prompt and tool-injection scanning uses a fixed phrase corpus that
  checks tool names, descriptions, prompts, args, and env values for
  instruction-override, exfiltration, secret-reveal, safety-bypass,
  shell-execution, file-write, and package-install phrases. No LLM
  judge is in the loop for the first release.
alternatives:
  - label: route every descriptor through an LLM judge
    rejected_because: |
      Judge scores drift across runs and providers. A CI gate that
      depends on a model call also depends on keys, network, and
      provider availability. The first release runs in CI with no
      vendor key.
  - label: train a small classifier on a labeled corpus
    rejected_because: |
      The labeled corpus does not exist yet. Building it before the
      static scanner has caught real configs reverses the order of
      cost and value.
rationale: |
  Findings need to be deterministic and easy to test. A fixed phrase
  corpus is explicit, easy to extend, and keeps every flagged
  descriptor traceable to the phrase that matched. The OpenAI Agents
  SDK direction explicitly assumes prompt-injection and exfiltration
  attempts; the corpus encodes that assumption.
evidence:
  - kind: spec
    ref: specs/0001-mcp-security-lab/requirements.md
  - kind: doc
    ref: https://openai.com/index/the-next-evolution-of-the-agents-sdk
rollback: |
  Delete the phrase corpus and the injection scanner module. The
  static config scan continues to work. A later DEC can supersede
  this one with an LLM-judge or classifier-based detector once the
  corpus has caught enough real cases to label.
owner: platform
---

## decision

Prompt and tool-injection scanning uses a fixed phrase corpus over
tool names, descriptions, prompts, args, and env values. The corpus
checks for instruction-override, exfiltration, secret-reveal,
safety-bypass, shell-execution, file-write, and package-install
phrases. No LLM judge is in the loop for the first release.

## alternatives

- Route every descriptor through an LLM judge. Rejected because
  judge scores drift and the gate would depend on keys, network, and
  provider availability.
- Train a small classifier on a labeled corpus. Rejected because the
  labeled corpus does not exist yet and building it before the
  scanner has caught real configs reverses the order of cost and
  value.

## rationale

Findings need to be deterministic and easy to test. A fixed phrase
corpus is explicit, easy to extend, and keeps every flagged
descriptor traceable to the phrase that matched.

## evidence

- `specs/0001-mcp-security-lab/requirements.md`
- OpenAI Agents SDK direction
  (https://openai.com/index/the-next-evolution-of-the-agents-sdk).

## rollback

Delete the phrase corpus and the injection scanner module. The static
config scan continues to work. A later DEC can supersede this one
once the corpus has caught enough real cases to label.

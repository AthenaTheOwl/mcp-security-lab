# DEC-MCPSEC-002: Policy corpus over LLM judge

## Status

Accepted

## Context

The MVP needs repeatable results. An LLM judge can explain nuance, but its score can drift across runs and providers.

## Decision

Use a fixed phrase corpus for prompt and tool-injection scanning. The corpus checks descriptors for phrases tied to instruction override, exfiltration, secret reveal, safety bypass, shell execution, file writes, and package install.

## Consequences

Findings are deterministic and easy to test. The scanner may miss paraphrases and multilingual attacks until the corpus grows.


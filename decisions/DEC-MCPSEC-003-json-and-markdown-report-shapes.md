# DEC-MCPSEC-003: JSON and Markdown report shapes

## Status

Accepted

## Context

Agent factory trust work needs both CI-friendly output and human review output.

## Decision

Every scan builds one internal report shape, writes JSON for machines, and renders Markdown for reviewers.

## Consequences

The CLI stays simple while downstream users can diff JSON, paste Markdown into review notes, or archive both as evidence.


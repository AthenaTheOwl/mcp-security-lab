# Requirements: MCP Security Lab

## Scope

MCP Security Lab scans static MCP server configuration before runtime and emits JSON plus Markdown risk and policy reports.

## Requirements

| ID | Requirement | owner_role |
| --- | --- | --- |
| R-MCPSEC-001 | Load common MCP config shapes: `mcpServers`, `servers`, and a flat server list. | owner_role:implementation_agent |
| R-MCPSEC-002 | Score each server with deterministic rules for stdio command startup, sensitive tool surfaces, remote URL auth gaps, wildcard env values, broad path roots, and read-only resource servers. | owner_role:implementation_agent |
| R-MCPSEC-003 | Scan tool names, descriptions, and prompts with a fixed injection phrase corpus. | owner_role:review_agent |
| R-MCPSEC-004 | Emit machine-readable JSON and reviewer-readable Markdown from the same scan. | owner_role:implementation_agent |
| R-MCPSEC-005 | Keep portfolio gates in CI for tests, voice lint, and spec trace coverage. | owner_role:planning_agent |
| R-MCPSEC-POL-001 | Evaluate a policy YAML file against each MCP server finding. | owner_role:implementation_agent |
| R-MCPSEC-POL-002 | Emit `allow`, `deny`, or `human_approval_required` per server and per tool. | owner_role:implementation_agent |
| R-MCPSEC-POL-003 | Include fixtures for local shell, broad filesystem, remote unauthenticated, and read-only resource servers. | owner_role:review_agent |
| R-MCPSEC-POL-004 | Exit nonzero when policy evaluation returns `deny` and the CLI is run with `--fail-on-deny`. | owner_role:implementation_agent |
| R-MCPSEC-DIFF-001 | Compare baseline and current JSON reports and classify added, removed, and changed server findings plus tool policy decisions. | owner_role:implementation_agent |
| R-MCPSEC-DIFF-002 | Exit nonzero from the diff CLI only when a configured gate detects net-new high or critical risk or a newly denied policy decision. | owner_role:implementation_agent |
| R-MCPSEC-MCPSURF-001 | Gate the athena-site MCP server tool surface against its committed snapshot; exit nonzero when added, removed, or changed tools are detected by name or input-schema hash. | owner_role:implementation_agent |
| R-MCPSEC-MCPSURF-002 | Emit a structured diff report conforming to `schemas/mcp-surface-diff.schema.json` whenever the gate runs, including drift_detected, summary counts, and per-tool entries for added/removed/changed. | owner_role:review_agent |

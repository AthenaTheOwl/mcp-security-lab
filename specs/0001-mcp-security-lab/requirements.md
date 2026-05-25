# Requirements: MCP Security Lab

## Scope

MCP Security Lab scans static MCP server configuration before runtime and emits JSON plus Markdown risk reports.

## Requirements

| ID | Requirement | owner_role |
| --- | --- | --- |
| R-MCPSEC-001 | Load common MCP config shapes: `mcpServers`, `servers`, and a flat server list. | owner_role:implementation_agent |
| R-MCPSEC-002 | Score each server with deterministic rules for stdio command startup, sensitive tool surfaces, remote URL auth gaps, wildcard env values, broad path roots, and read-only resource servers. | owner_role:implementation_agent |
| R-MCPSEC-003 | Scan tool names, descriptions, and prompts with a fixed injection phrase corpus. | owner_role:review_agent |
| R-MCPSEC-004 | Emit machine-readable JSON and reviewer-readable Markdown from the same scan. | owner_role:implementation_agent |
| R-MCPSEC-005 | Keep portfolio gates in CI for tests, voice lint, and spec trace coverage. | owner_role:planning_agent |


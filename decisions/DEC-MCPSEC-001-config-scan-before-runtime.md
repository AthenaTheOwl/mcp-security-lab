---
id: DEC-MCPSEC-001-config-scan-before-runtime
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-001
date: 2026-05-25
status: approved
reversible: true
decision: |
  MCP Security Lab scans static MCP server configuration before the
  server process launches. The scanner never connects to the server
  and never executes any startup command during analysis.
alternatives:
  - label: probe the live server over stdio or HTTP
    rejected_because: |
      Live probing requires the harness to invoke the very command
      under review, which is the failure mode the tool is meant to
      catch. It also makes the gate non-deterministic and slow.
  - label: combine static scan with sandboxed live probe
    rejected_because: |
      A sandbox raises the implementation cost (container, network
      policy, lifecycle) without changing the static signals the
      first release catches. Sandbox probing lands in a later pass
      after the static scanner has caught real configs.
rationale: |
  Source-controlled config is the right surface for a CI gate. The
  MCP security guidance treats local startup commands, broad scopes,
  HTTP auth gaps, SSRF paths, and sandboxing as first-order review
  items. Static analysis hits all of those without granting tool
  execution rights to the scanner.
evidence:
  - kind: spec
    ref: specs/0001-mcp-security-lab/requirements.md
  - kind: doc
    ref: https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices
  - kind: doc
    ref: https://docs.anthropic.com/en/docs/claude-code/security
rollback: |
  Remove this DEC and the static scanner module. No external state
  changes are required because the scanner only reads config files
  and writes reports under `reports/`. A later release could replace
  static scanning with live probing by superseding this DEC.
owner: platform
---

## decision

MCP Security Lab scans static MCP server configuration before the
server process launches. The scanner never connects to the server and
never executes any startup command during analysis.

## alternatives

- Probe the live server over stdio or HTTP. Rejected because the
  harness would invoke the very command under review and the gate
  would lose determinism.
- Combine static scan with sandboxed live probe. Rejected because a
  sandbox raises implementation cost without changing the static
  signals the first release catches.

## rationale

Source-controlled config is the right surface for a CI gate. Static
analysis covers MCP server startup commands, broad scopes, HTTP auth
gaps, SSRF paths, and resource descriptors without granting tool
execution rights to the scanner.

## evidence

- `specs/0001-mcp-security-lab/requirements.md`
- MCP security best practices
  (https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices).
- Claude Code security docs
  (https://docs.anthropic.com/en/docs/claude-code/security).

## rollback

Remove this DEC and the static scanner module. The scanner only reads
config files and writes reports under `reports/`, so no external state
changes need to be undone. A later release could replace static
scanning with live probing by superseding this DEC.

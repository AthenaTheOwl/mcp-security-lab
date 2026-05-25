# MCP Security Lab

MCP Security Lab is a 30-second preflight check for Model Context Protocol server configs. Point it at a Claude Desktop style config, a `servers` list, or a flat list of server entries and it flags command execution, broad filesystem access, unauthenticated remote transports, sensitive tool keywords, and prompt or tool-injection language before those servers run.

This repo follows three current security signals:

- The MCP security guidance treats local server startup commands, broad scopes, HTTP auth gaps, SSRF paths, and sandboxing as first-order review items: [MCP security best practices](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices).
- Claude Code security docs place MCP servers behind source-controlled configuration, permission settings, trust checks, and user review: [Claude Code security](https://docs.anthropic.com/en/docs/claude-code/security).
- OpenAI's Agents SDK direction assumes prompt injection and exfiltration attempts, and separates agent harness from sandbox compute: [Agents SDK evolution](https://openai.com/index/the-next-evolution-of-the-agents-sdk).

## For your role

- Security reviewer: get a deterministic triage report before an MCP server enters an allowlist.
- Agent platform engineer: turn config review into a repeatable CI gate.
- Founder or hiring manager: see a small, public-read artifact that connects agent trust claims to code, specs, decisions, and tests.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

```powershell
python -m mcp_security_lab scan examples/claude-desktop-config.json --out report.json
```

The command writes `report.json` and `report.md`. To choose the Markdown path:

```powershell
python -m mcp_security_lab scan examples/risky-filesystem-shell-server.json --out reports/risky.json --markdown reports/risky.md
```

## What it catches

- `stdio` MCP servers that start local commands.
- Tool names, descriptions, prompts, args, env, and scopes that mention filesystem, shell, process, git, network, browser, email, database, secret, or env access.
- Remote URL transports that lack auth metadata in config.
- Wildcard env values and broad root paths such as `/`, `C:\`, `%USERPROFILE%`, or `$HOME`.
- Injection phrases such as `ignore previous`, `exfiltrate`, `reveal secrets`, `disable safety`, `run shell`, `write file`, and `install package`.
- Read-only resource servers, which get a lower score when they avoid command execution and unauthenticated remote access.

## What it does not catch

- Runtime behavior after the server starts.
- Supply-chain risk inside an npm, Python, or binary package.
- Whether auth metadata is valid, scoped, or rotated.
- Hidden prompt text returned after connection.
- Network destination safety beyond static URL and metadata checks.

## Development gates

```powershell
python -m pytest
python scripts/voice_lint.py
python scripts/spec_check.py
python scripts/validate_decisions.py
python scripts/validate_roles.py
python scripts/validate_tools.py
python scripts/validate_policies.py
python scripts/validate_skills.py
python scripts/validate_dreams.py
python scripts/check_schema_cache_freshness.py
python -m mcp_security_lab scan examples/claude-desktop-config.json --out reports/example.json
```

## Governance

This repo runs under the Cognitive Delivery Control Plane charter at
[`athena-site/ops/control-plane.md`](https://github.com/AthenaTheOwl/athena-site/blob/main/ops/control-plane.md).
The charter names six artifact types (specs, decisions, dreams,
ledgers, schemas, policies) and the cross-repo schemas that gate
each. Local artifacts:

- `specs/0001-mcp-security-lab/` names the R-MCPSEC-* requirements.
- `decisions/DEC-MCPSEC-*.md` records each architectural choice.
- `.agents/` holds the six minimum-viable roles, the tool registry,
  the policy set, the state-machines, and the workflows.
- `dreams/` reserves the shape for the weekly offline-cognition pass.
- `ops/RELEASE_LEDGER.md` and `ops/RESET_LEDGER.md` carry the audit
  trail; `ops/event-log/` holds the structured event stream.

## License

MIT. See [LICENSE](LICENSE).


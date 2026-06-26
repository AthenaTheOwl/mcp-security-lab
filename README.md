# mcp-security-lab

A Claude Desktop config lists three MCP servers. One of them starts a local
shell, can write files, and carries six injection phrases in its tool text. It
scores 100 out of 100 and the policy says deny. The other two are a remote ticket
tool that needs a human to approve it and a read-only docs server that's fine. You
learn this before any of the three connect.

## What it does

An MCP server is a process your agent trusts. Before it joins the allowlist,
someone has to read the config and decide whether trusting it is a mistake. That
read is the kind of work that gets skipped when there are three servers and a
deadline, and skipping it is how a server that starts a shell ends up inside the
loop.

mcp-security-lab does the read deterministically. Point it at a Claude Desktop
config, a `servers` list, or a flat list of entries. It scores each server 0 to
100, flags the surfaces that earn the score — local command execution, broad
filesystem roots, remote transports with no auth metadata, sensitive tool
keywords, prompt- and tool-injection language — and, if you hand it a policy,
stamps each server allow, deny, or human-approval-required. No runtime, no
network. It reads what the config already says and tells you what you'd have
agreed to.

It does not watch the server after it starts, vet the package behind the command,
or judge whether the auth it found is real. It catches the things that are
visible at review time, which is the moment you still have the choice.

## Try it

One command, no arguments, no network. It reads the committed example report and
prints a ranked review:

```text
$ python -m mcp_security_lab show
MCP Security Lab - config risk review
source: examples\claude-desktop-config.json
servers: 3   max score: 100   risk: low=1 medium=0 high=1 critical=1

servers ranked by risk score:

   #  score  level     transport  verdict                 server
  --  -----  --------  ---------  ----------------------  ------------------------
   1    100  critical  stdio      deny                    local-filesystem-shell
   2     51  high      sse        human_approval_required  remote-ticket-tools
   3      5  low       sse        allow                   docs-readonly

highest-risk server: local-filesystem-shell (score 100, critical)
  flagged: STDIO-COMMAND (high), FILESYSTEM-SURFACE (medium), SENSITIVE-KEYWORDS (medium), BROAD-ACCESS (medium), INJECTION-CORPUS (high)
  injection phrases (6): ignore previous, reveal secrets, run shell, write file

policy verdicts: allow=1, human_approval_required=1, deny=1
  denied (do not allowlist): local-filesystem-shell
```

Ranked worst first. The server at the top is the one you do not allowlist, and the
line under it says why.

## Live demo

an interactive page that mirrors `python -m mcp_security_lab show`: the config
risk review table, summary metrics, and the highest-risk server with its
injection phrases and policy verdict. it reads the committed
`reports/example.json` directly — no network, no secrets.

run locally:

```powershell
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

deploy on streamlit community cloud: new app -> repo `AthenaTheOwl/mcp-security-lab`,
branch `main`, main file `streamlit_app.py`.

<!-- live url: https://share.streamlit.io/... -->

## What it catches

- `stdio` servers that start a local command.
- Tool names, descriptions, prompts, args, env, and scopes that mention
  filesystem, shell, process, git, network, browser, email, database, secret, or
  env access.
- Remote URL transports with no auth metadata in the config.
- Wildcard env values and broad roots like `/`, `C:\`, `%USERPROFILE%`, `$HOME`.
- Injection phrases: `ignore previous`, `exfiltrate`, `reveal secrets`,
  `disable safety`, `run shell`, `write file`, `install package`.
- Read-only resource servers, which score lower when they avoid command
  execution and unauthenticated remote access.
- Optional YAML policy verdicts per server and declared tool.
- Drift between an approved baseline report and the current one — new findings,
  changed tool decisions, freshly introduced high/critical risk, a new `deny`.

It stops where review stops. Runtime behavior, supply-chain risk inside the
package, whether the auth is valid, hidden text returned after connection, and
network-destination safety past the static URL are all outside what a config can
tell you, and the tool says so rather than pretending otherwise.

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Scan a config, with and without a policy:

```powershell
python -m mcp_security_lab scan examples/claude-desktop-config.json --out report.json
python -m mcp_security_lab scan examples/claude-desktop-config.json --policy examples/policies/default.yaml --fail-on-deny --out report.json
```

The command writes `report.json` and `report.md`. Choose the Markdown path
yourself with `--markdown`:

```powershell
python -m mcp_security_lab scan examples/risky-filesystem-shell-server.json --out reports/risky.json --markdown reports/risky.md
```

Compare an approved baseline with the current report in CI. It exits nonzero only
when a fail flag finds net-new high or critical risk or a newly denied decision:

```powershell
python -m mcp_security_lab diff --baseline reports/baseline.json --current reports/current.json --out reports/diff.json --fail-on-new-critical --fail-on-new-deny
```

## How it connects

This is the trust check at the front of the agent. The control plane it runs
under, and where the cross-repo schemas live, is
[athena-site](https://github.com/AthenaTheOwl/athena-site/blob/main/ops/control-plane.md)
— the charter names six artifact types (specs, decisions, dreams, ledgers,
schemas, policies) and gates each. Local copies of those artifacts sit here:

- `specs/0001-mcp-security-lab/` names the R-MCPSEC-* requirements.
- `decisions/DEC-MCPSEC-*.md` records each architectural choice.
- `.agents/` holds the six roles, the tool registry, the policy set, the state
  machines, and the workflows.
- `dreams/` reserves the shape for the weekly offline-cognition pass.
- `ops/RELEASE_LEDGER.md`, `ops/RESET_LEDGER.md`, and `ops/event-log/` carry the
  audit trail.

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
python -m mcp_security_lab scan examples/claude-desktop-config.json --policy examples/policies/default.yaml --out reports/example.json
python -m mcp_security_lab diff --baseline tests/fixtures/diff-baseline-report.json --current tests/fixtures/diff-current-clean-report.json --out reports/example-diff.json --fail-on-new-critical --fail-on-new-deny
```

## License

MIT. See [LICENSE](LICENSE).

# Real-Config Scanner Scorecard

Precision / recall of the static MCP config scanner measured against **25 real, publicly documented** MCP server configurations (25 servers) — not self-authored synthetic fixtures. Corpus and provenance: `eval/manifest.json`; ground truth: `eval/labels.json`. Regenerate with `python scripts/generate_eval_scorecard.py`.

This scorecard is deterministic: it is recomputed from the committed corpus and asserted in `tests/test_eval_scorecard.py`, so any scanner change that shifts precision/recall fails CI.

## Corpus

- Configs: 25 | Servers: 25 | Curated: 2026-07-05
- Public sources only; secret values kept as upstream placeholders.

| Source repo | Configs |
| --- | ---: |
| `geelen/mcp-remote` | 2 |
| `github/github-mcp-server` | 2 |
| `modelcontextprotocol/servers` | 12 |
| `modelcontextprotocol/servers-archived` | 9 |

## Precision / recall

Each category maps to one scanner rule. A cell is one (config x server x category) decision. `support+` = ground-truth-positive cells.

| Category | Rule | TP | FP | FN | TN | support+ | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| COMMAND_EXECUTION | `STDIO-COMMAND` | 23 | 0 | 0 | 2 | 23 | 100.0% | 100.0% | 100.0% |
| BROAD_FILESYSTEM | `BROAD-ACCESS` | 1 | 0 | 0 | 24 | 1 | 100.0% | 100.0% | 100.0% |
| UNAUTH_REMOTE | `REMOTE-NO-AUTH` | 2 | 0 | 0 | 23 | 2 | 100.0% | 100.0% | 100.0% |
| PROMPT_INJECTION | `INJECTION-CORPUS` | 0 | 0 | 0 | 25 | 0 | n/a | n/a | n/a |
| **Overall (micro)** | — | 26 | 0 | 0 | 74 | 26 | 100.0% | 100.0% | 100.0% |

## False positives

None. The scanner raised zero false alarms across the four decision categories on this corpus.

## False negatives

None.

## Ground-truth definitions

- **COMMAND_EXECUTION**: Config causes a local process/command to start (stdio server).
- **BROAD_FILESYSTEM**: Config grants filesystem access to an entire user home dir, a filesystem root (/, C:\), or via a path wildcard (*).
- **UNAUTH_REMOTE**: Config declares a remote (URL/HTTP/SSE) MCP transport and carries NO in-config auth material (Authorization header / token).
- **PROMPT_INJECTION**: Config descriptor text (names/descriptions/prompts) contains prompt- or tool-injection language.

## Ambiguous labels

- `05-git-docker-home-mount`: Docker bind-mount of the whole $HOME. Labelled BROAD_FILESYSTEM TRUE (exposes all of home), though a git tool nominally scopes to repos.
- `22-mcp-remote-sse-noauth`: Remote SSE transport expressed via a stdio proxy command. Labelled UNAUTH_REMOTE TRUE (unauthenticated remote endpoint) and COMMAND_EXECUTION TRUE (a local npx process does start).
- `24-github-remote-http-oauth`: OAuth is negotiated at runtime; the config file itself carries no auth material, so UNAUTH_REMOTE TRUE by the in-config definition.

## Scope note

`PROMPT_INJECTION` has zero positive support: real `claude_desktop_config.json` files carry only `command`/`args`/`env`, never tool descriptions or prompts, so the injection corpus (the scanner's most sophisticated feature) has no attack surface in the artifact it scans. Injection risk lives in runtime tool metadata, which is out of static-config scope. Precision/recall are therefore undefined (n/a) for that category here, with zero false alarms.

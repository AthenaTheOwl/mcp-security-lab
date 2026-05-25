# Traceability: MCP Security Lab

| Requirement | Code or artifact | Decision coverage |
| --- | --- | --- |
| R-MCPSEC-001 | `src/mcp_security_lab/config.py`, `tests/test_loader.py` | DEC-MCPSEC-001-config-scan-before-runtime |
| R-MCPSEC-002 | `src/mcp_security_lab/scoring.py`, `tests/test_scoring.py` | DEC-MCPSEC-001-config-scan-before-runtime |
| R-MCPSEC-003 | `src/mcp_security_lab/injection.py`, `tests/test_scoring.py` | DEC-MCPSEC-002-policy-corpus-over-llm-judge |
| R-MCPSEC-004 | `src/mcp_security_lab/report.py`, `tests/test_report.py` | DEC-MCPSEC-003-json-and-markdown-report-shapes |
| R-MCPSEC-005 | `.github/workflows/ci.yml`, `scripts/voice_lint.py`, `scripts/spec_check.py` | DEC-MCPSEC-003-json-and-markdown-report-shapes |


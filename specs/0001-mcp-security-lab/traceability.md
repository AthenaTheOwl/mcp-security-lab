# Traceability: MCP Security Lab

| Requirement | Code or artifact | Decision coverage |
| --- | --- | --- |
| R-MCPSEC-001 | `mcp_security_lab/config.py`, `tests/test_loader.py` | DEC-MCPSEC-001-config-scan-before-runtime |
| R-MCPSEC-002 | `mcp_security_lab/scoring.py`, `tests/test_scoring.py` | DEC-MCPSEC-001-config-scan-before-runtime |
| R-MCPSEC-003 | `mcp_security_lab/injection.py`, `tests/test_scoring.py` | DEC-MCPSEC-002-policy-corpus-over-llm-judge |
| R-MCPSEC-004 | `mcp_security_lab/report.py`, `tests/test_report.py` | DEC-MCPSEC-003-json-and-markdown-report-shapes |
| R-MCPSEC-005 | `.github/workflows/ci.yml`, `scripts/voice_lint.py`, `scripts/spec_check.py` | DEC-MCPSEC-003-json-and-markdown-report-shapes |
| R-MCPSEC-POL-001 | `mcp_security_lab/policy.py`, `examples/policies/default.yaml`, `tests/test_policy.py` | DEC-MCPSEC-005-policy-evaluation-over-score-only-warnings |
| R-MCPSEC-POL-002 | `mcp_security_lab/report.py`, `mcp_security_lab/policy.py`, `tests/test_policy.py` | DEC-MCPSEC-005-policy-evaluation-over-score-only-warnings |
| R-MCPSEC-POL-003 | `tests/fixtures/*.json`, `tests/test_policy.py` | DEC-MCPSEC-005-policy-evaluation-over-score-only-warnings |
| R-MCPSEC-POL-004 | `mcp_security_lab/cli.py`, `tests/test_policy.py` | DEC-MCPSEC-005-policy-evaluation-over-score-only-warnings |
| R-MCPSEC-DIFF-001 | `mcp_security_lab/diff.py`, `tests/fixtures/diff-*.json`, `tests/test_diff.py` | DEC-MCPSEC-006-baseline-current-diff-gate |
| R-MCPSEC-DIFF-002 | `mcp_security_lab/cli.py`, `mcp_security_lab/diff.py`, `tests/test_diff.py` | DEC-MCPSEC-006-baseline-current-diff-gate |

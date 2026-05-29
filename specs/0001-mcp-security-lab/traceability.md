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
| R-MCPSEC-MCPSURF-001 | `scripts/validate_athena_mcp_surface.py`, `tests/test_validate_athena_mcp_surface.py`, `.github/workflows/ci.yml` | DEC-MCPSEC-007-athena-mcp-surface-drift-gate |
| R-MCPSEC-MCPSURF-002 | `schemas/mcp-surface-diff.schema.json`, `scripts/validate_athena_mcp_surface.py` (build_diff_report), `tests/test_validate_athena_mcp_surface.py` (test_report_conforms_to_diff_schema) | DEC-MCPSEC-007-athena-mcp-surface-drift-gate |
| R-MCPSEC-MCPSURF-003 | `config/mcp_server_registry.yaml`, `scripts/validate_mcp_surface.py`, `tests/test_validate_mcp_surface_registry.py` (test_main_server_id_targets_one, test_main_all_clean) | DEC-MCPSEC-008-mcp-server-agnostic-drift-gate |
| R-MCPSEC-MCPSURF-004 | `scripts/validate_mcp_surface.py` (per-server report path, default-all), `.github/workflows/ci.yml`, `tests/test_validate_mcp_surface_registry.py` (test_main_no_flag_defaults_to_all, test_main_one_drifts_exits_one) | DEC-MCPSEC-008-mcp-server-agnostic-drift-gate |
| R-MCPSEC-MCPSURF-005 | `scripts/validate_mcp_surface.py` (load_registry), `tests/test_validate_mcp_surface_registry.py` (test_load_registry_malformed_yaml, test_load_registry_missing_required_field, test_load_registry_duplicate_ids, test_load_registry_enabled_wrong_type, test_main_disabled_server_is_skipped) | DEC-MCPSEC-008-mcp-server-agnostic-drift-gate |
| R-MCPSEC-010 | `ops/schemas-cache/decision.schema.json`, `ops/schemas-cache/dream-output.schema.json`, `ops/schemas-cache/run.schema.json` | DEC-MCPSEC-009-systems-thinking-discipline-adoption |
| R-MCPSEC-011 | `.agents/AGENTS.md` (Systems-thinking discipline section) | DEC-MCPSEC-009-systems-thinking-discipline-adoption |
| R-MCPSEC-012 | `scripts/validate_decisions.py` (check_systems_thinking_fields, SYSTEMS_THINKING_FIELDS) | DEC-MCPSEC-009-systems-thinking-discipline-adoption |
| R-MCPSEC-013 | `decisions/DEC-MCPSEC-006-baseline-current-diff-gate.md`, `decisions/DEC-MCPSEC-007-athena-mcp-surface-drift-gate.md`, `decisions/DEC-MCPSEC-008-mcp-server-agnostic-drift-gate.md` | DEC-MCPSEC-009-systems-thinking-discipline-adoption |

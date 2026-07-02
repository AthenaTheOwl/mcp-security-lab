from __future__ import annotations

import json
from pathlib import Path

from mcp_security_lab.cli import main
from mcp_security_lab.diff import build_diff_report, load_report, render_diff_markdown


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
BASELINE = FIXTURES / "diff-baseline-report.json"
CLEAN_CURRENT = FIXTURES / "diff-current-clean-report.json"
NEW_CRITICAL_CURRENT = FIXTURES / "diff-current-new-critical-report.json"
NEW_DENY_CURRENT = FIXTURES / "diff-current-new-deny-report.json"
INPLACE_ESCALATION_CURRENT = FIXTURES / "diff-current-inplace-escalation-report.json"
ADDED_FINDING_CURRENT = FIXTURES / "diff-current-added-finding-report.json"


def test_clean_diff_has_no_gate_signals() -> None:
    diff = build_diff_report(
        load_report(BASELINE),
        load_report(CLEAN_CURRENT),
        BASELINE,
        CLEAN_CURRENT,
    )

    assert diff["summary"]["unchanged_servers"] == 1
    assert diff["summary"]["new_high_or_critical_risk"] == 0
    assert diff["summary"]["new_deny_decisions"] == 0
    assert diff["servers"][0]["status"] == "unchanged"


def test_new_critical_diff_classifies_added_server_and_fails_when_configured(
    tmp_path: Path,
) -> None:
    out = tmp_path / "diff.json"

    result = main(
        [
            "diff",
            "--baseline",
            str(BASELINE),
            "--current",
            str(NEW_CRITICAL_CURRENT),
            "--out",
            str(out),
            "--fail-on-new-critical",
        ]
    )

    assert result == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["summary"]["added_servers"] == 1
    assert payload["summary"]["new_high_or_critical_risk"] >= 1
    assert out.with_suffix(".md").is_file()


def test_new_deny_diff_fails_only_when_deny_gate_is_configured(tmp_path: Path) -> None:
    out = tmp_path / "diff.json"

    no_gate_result = main(
        [
            "diff",
            "--baseline",
            str(BASELINE),
            "--current",
            str(NEW_DENY_CURRENT),
            "--out",
            str(out),
        ]
    )
    deny_gate_result = main(
        [
            "diff",
            "--baseline",
            str(BASELINE),
            "--current",
            str(NEW_DENY_CURRENT),
            "--out",
            str(out),
            "--fail-on-new-deny",
        ]
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert no_gate_result == 0
    assert deny_gate_result == 1
    assert payload["summary"]["new_deny_decisions"] == 1
    assert payload["servers"][0]["tool_decisions"]["added"][0]["name"] == "write_file"


def test_inplace_server_escalation_flags_server_scope_risk_and_deny() -> None:
    # An existing server (present in baseline as low/allow) escalates in place to
    # critical/deny. This exercises the server-scope branches:
    # baseline_level not in HIGH_OR_CRITICAL, and baseline_verdict != deny.
    diff = build_diff_report(
        load_report(BASELINE),
        load_report(INPLACE_ESCALATION_CURRENT),
        BASELINE,
        INPLACE_ESCALATION_CURRENT,
    )
    entry = diff["servers"][0]

    assert entry["status"] == "changed"
    assert entry["new_high_or_critical_risks"] == [
        {
            "scope": "server",
            "server": "docs-readonly",
            "risk_level": "critical",
            "baseline_risk_level": "low",
        },
        {
            "scope": "finding",
            "server": "docs-readonly",
            "rule_id": "STDIO-COMMAND",
            "severity": "high",
        },
    ]
    assert entry["new_deny_decisions"] == [
        {
            "scope": "server",
            "server": "docs-readonly",
            "verdict": "deny",
            "reasons": ["Local command server has broad filesystem or wildcard access."],
        }
    ]


def test_added_high_finding_on_present_server_flags_finding_scope_only() -> None:
    # An already-present server keeps its low/allow snapshot but gains a
    # high-severity finding. This isolates the added-finding branch from the
    # server-level and added-server paths: no server-scope risk, no new deny.
    diff = build_diff_report(
        load_report(BASELINE),
        load_report(ADDED_FINDING_CURRENT),
        BASELINE,
        ADDED_FINDING_CURRENT,
    )
    entry = diff["servers"][0]

    assert entry["status"] == "changed"
    assert diff["summary"]["added_servers"] == 0
    assert entry["new_high_or_critical_risks"] == [
        {
            "scope": "finding",
            "server": "docs-readonly",
            "rule_id": "INJECTION-CORPUS",
            "severity": "high",
        }
    ]
    assert entry["new_deny_decisions"] == []


def test_diff_markdown_renders_summary_table() -> None:
    diff = build_diff_report(
        load_report(BASELINE),
        load_report(NEW_DENY_CURRENT),
        BASELINE,
        NEW_DENY_CURRENT,
    )
    markdown = render_diff_markdown(diff)

    assert "# MCP Security Lab Diff" in markdown
    assert "| docs-readonly | changed | low | low |" in markdown
    assert "- New deny decisions: 1" in markdown

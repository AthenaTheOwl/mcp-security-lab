from __future__ import annotations

import json

from mcp_security_lab.config import ServerConfig
from mcp_security_lab.report import (
    build_report,
    render_markdown,
    render_show,
    write_reports,
)


def test_report_contains_summary_and_server() -> None:
    report = build_report([ServerConfig("alpha", {"command": "node"})], source="config.json")  # type: ignore[arg-type]

    assert report["summary"]["server_count"] == 1
    assert report["servers"][0]["name"] == "alpha"
    assert "INJECT-IGNORE_PREVIOUS" in report["policy_corpus"]


def test_markdown_renders_table() -> None:
    report = build_report([ServerConfig("alpha", {"command": "node"})], source="config.json")  # type: ignore[arg-type]
    markdown = render_markdown(report)

    assert "# MCP Security Lab Report" in markdown
    assert "| alpha | stdio |" in markdown


def test_write_reports_creates_json_and_markdown(tmp_path) -> None:
    report = build_report([ServerConfig("alpha", {"command": "node"})], source="config.json")  # type: ignore[arg-type]
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"

    write_reports(report, json_path, markdown_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["servers"][0]["name"] == "alpha"
    assert "MCP Security Lab Report" in markdown_path.read_text(encoding="utf-8")


def test_render_show_ranks_servers_by_risk() -> None:
    report = {
        "source": "config.json",
        "summary": {
            "server_count": 2,
            "max_score": 100,
            "risk_counts": {"low": 1, "medium": 0, "high": 0, "critical": 1},
        },
        "servers": [
            {
                "name": "safe-one",
                "risk_score": 5,
                "risk_level": "low",
                "transport": "sse",
                "read_only": True,
                "findings": [],
                "injection_matches": [],
                "policy": {"verdict": "allow"},
            },
            {
                "name": "risky-one",
                "risk_score": 100,
                "risk_level": "critical",
                "transport": "stdio",
                "read_only": False,
                "findings": [
                    {
                        "rule_id": "STDIO-COMMAND",
                        "severity": "high",
                        "score_delta": 60,
                    }
                ],
                "injection_matches": [
                    {"rule_id": "INJECT-RUN_SHELL", "match": "run shell"}
                ],
                "policy": {"verdict": "deny"},
            },
        ],
        "policy": {
            "verdict_counts": {
                "allow": 1,
                "human_approval_required": 0,
                "deny": 1,
            }
        },
    }

    text = render_show(report)

    # highest-risk server is ranked first
    risky_pos = text.index("risky-one")
    safe_pos = text.index("safe-one")
    assert risky_pos < safe_pos
    assert "servers ranked by risk score" in text
    assert "highest-risk server: risky-one" in text
    assert "run shell" in text
    assert "denied (do not allowlist): risky-one" in text


def test_render_show_handles_missing_policy() -> None:
    report = build_report([ServerConfig("alpha", {"command": "node"})], source="config.json")  # type: ignore[arg-type]
    text = render_show(report)
    assert "alpha" in text
    assert "servers ranked by risk score" in text


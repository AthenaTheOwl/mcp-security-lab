from __future__ import annotations

import json

from mcp_security_lab.config import ServerConfig
from mcp_security_lab.report import build_report, render_markdown, write_reports


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


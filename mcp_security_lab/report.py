from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ServerConfig
from .injection import INJECTION_PATTERNS
from .scoring import score_server


def build_report(servers: list[ServerConfig], source: Path) -> dict[str, Any]:
    scored = [score_server(server) for server in servers]
    risk_counts = {level: 0 for level in ("low", "medium", "high", "critical")}
    for server in scored:
        risk_counts[server["risk_level"]] += 1
    return {
        "schema_version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": str(source),
        "summary": {
            "server_count": len(scored),
            "max_score": max((server["risk_score"] for server in scored), default=0),
            "risk_counts": risk_counts,
        },
        "policy_corpus": sorted(f"INJECT-{name.upper()}" for name in INJECTION_PATTERNS),
        "servers": scored,
    }


def write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# MCP Security Lab Report",
        "",
        f"Source: `{report['source']}`",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Servers scanned: {report['summary']['server_count']}",
        f"- Max score: {report['summary']['max_score']}",
        f"- Risk counts: {_risk_count_text(report['summary']['risk_counts'])}",
        "",
        "## Servers",
        "",
        "| Server | Transport | Score | Level | Read-only |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for server in report["servers"]:
        lines.append(
            f"| {server['name']} | {server['transport']} | {server['risk_score']} | "
            f"{server['risk_level']} | {str(server['read_only']).lower()} |"
        )
    lines.extend(["", "## Findings", ""])
    for server in report["servers"]:
        lines.append(f"### {server['name']}")
        if not server["findings"]:
            lines.append("")
            lines.append("- No findings.")
        else:
            lines.append("")
            for finding in server["findings"]:
                lines.append(
                    f"- `{finding['rule_id']}` ({finding['severity']}, {finding['score_delta']:+}): "
                    f"{finding['message']} [{finding['evidence']}]"
                )
        if server["injection_matches"]:
            lines.append("")
            lines.append("Injection matches:")
            for match in server["injection_matches"]:
                lines.append(f"- `{match['rule_id']}` in `{match['field']}`: {match['evidence']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _risk_count_text(counts: dict[str, int]) -> str:
    return ", ".join(f"{level}={counts[level]}" for level in ("low", "medium", "high", "critical"))


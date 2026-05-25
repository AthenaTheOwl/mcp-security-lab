from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ServerConfig
from .injection import INJECTION_PATTERNS
from .policy import evaluate_policy_for_server
from .scoring import score_server


def build_report(
    servers: list[ServerConfig],
    source: Path,
    policy: dict[str, Any] | None = None,
    policy_source: Path | None = None,
) -> dict[str, Any]:
    scored = [score_server(server) for server in servers]
    if policy is not None:
        for server, scored_server in zip(servers, scored):
            scored_server["policy"] = evaluate_policy_for_server(policy, server, scored_server)

    risk_counts = {level: 0 for level in ("low", "medium", "high", "critical")}
    for server in scored:
        risk_counts[server["risk_level"]] += 1
    report = {
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
    if policy is not None:
        report["policy"] = {
            "source": str(policy_source) if policy_source is not None else None,
            "schema_version": str(policy.get("schema_version", "unknown")),
            "verdict_counts": _policy_verdict_counts(scored),
        }
    return report


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
    ]
    if "policy" in report:
        lines.extend(_render_policy_markdown(report))
    lines.extend(
        [
            "## Servers",
            "",
            "| Server | Transport | Score | Level | Read-only |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
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


def _policy_verdict_counts(servers: list[dict[str, Any]]) -> dict[str, int]:
    counts = {verdict: 0 for verdict in ("allow", "human_approval_required", "deny")}
    for server in servers:
        policy = server.get("policy")
        if not isinstance(policy, dict):
            continue
        counts[str(policy["verdict"])] += 1
    return counts


def _render_policy_markdown(report: dict[str, Any]) -> list[str]:
    counts = report["policy"]["verdict_counts"]
    lines = [
        "## Policy",
        "",
        f"- Policy: `{report['policy']['source']}`",
        (
            "- Server verdicts: "
            f"allow={counts['allow']}, "
            f"human_approval_required={counts['human_approval_required']}, "
            f"deny={counts['deny']}"
        ),
        "",
        "| Server | Verdict | Reasons | Tool verdicts |",
        "| --- | --- | --- | --- |",
    ]
    for server in report["servers"]:
        policy = server["policy"]
        tools = policy.get("tools", [])
        tool_text = (
            "; ".join(f"{tool['name']}={tool['verdict']}" for tool in tools)
            or "none"
        )
        lines.append(
            f"| {_markdown_cell(server['name'])} | `{policy['verdict']}` | "
            f"{_markdown_cell('; '.join(policy['reasons']))} | {_markdown_cell(tool_text)} |"
        )
    lines.append("")
    return lines


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")

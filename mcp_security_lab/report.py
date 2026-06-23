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


def render_show(report: dict[str, Any]) -> str:
    """Render a committed report as a ranked, human-readable summary."""
    servers = sorted(
        report["servers"],
        key=lambda s: s["risk_score"],
        reverse=True,
    )
    summary = report["summary"]
    counts = summary["risk_counts"]

    lines = [
        "MCP Security Lab - config risk review",
        f"source: {report['source']}",
        (
            f"servers: {summary['server_count']}   "
            f"max score: {summary['max_score']}   "
            f"risk: low={counts['low']} medium={counts['medium']} "
            f"high={counts['high']} critical={counts['critical']}"
        ),
        "",
        "servers ranked by risk score:",
        "",
        f"  {'#':>2}  {'score':>5}  {'level':<8}  {'transport':<9}  {'verdict':<22}  server",
        f"  {'-' * 2}  {'-' * 5}  {'-' * 8}  {'-' * 9}  {'-' * 22}  {'-' * 24}",
    ]
    for rank, server in enumerate(servers, start=1):
        policy = server.get("policy")
        verdict = policy["verdict"] if isinstance(policy, dict) else "-"
        lines.append(
            f"  {rank:>2}  {server['risk_score']:>5}  {server['risk_level']:<8}  "
            f"{server['transport']:<9}  {verdict:<22}  {server['name']}"
        )

    top = servers[0]
    top_findings = [
        f"{f['rule_id']} ({f['severity']})"
        for f in top["findings"]
        if f["severity"] in ("high", "critical") or f["score_delta"] > 0
    ]
    inj = top.get("injection_matches", [])
    lines.extend(
        [
            "",
            f"highest-risk server: {top['name']} (score {top['risk_score']}, {top['risk_level']})",
        ]
    )
    if top_findings:
        lines.append("  flagged: " + ", ".join(top_findings))
    if inj:
        phrases = sorted({m["match"].lower() for m in inj})
        lines.append(f"  injection phrases ({len(inj)}): " + ", ".join(phrases))

    if "policy" in report:
        vc = report["policy"]["verdict_counts"]
        denied = [
            s["name"]
            for s in servers
            if isinstance(s.get("policy"), dict) and s["policy"]["verdict"] == "deny"
        ]
        lines.append("")
        lines.append(
            "policy verdicts: "
            f"allow={vc['allow']}, "
            f"human_approval_required={vc['human_approval_required']}, "
            f"deny={vc['deny']}"
        )
        if denied:
            lines.append("  denied (do not allowlist): " + ", ".join(denied))

    return "\n".join(lines) + "\n"


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

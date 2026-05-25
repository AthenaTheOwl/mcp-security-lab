from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HIGH_OR_CRITICAL = {"high", "critical"}


def load_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON report object")
    if not isinstance(data.get("servers"), list):
        raise ValueError(f"{path} must contain a servers list")
    return data


def build_diff_report(
    baseline: dict[str, Any],
    current: dict[str, Any],
    baseline_source: Path,
    current_source: Path,
) -> dict[str, Any]:
    baseline_servers = _servers_by_name(baseline)
    current_servers = _servers_by_name(current)
    entries = [
        _diff_server(name, baseline_servers.get(name), current_servers.get(name))
        for name in sorted(set(baseline_servers) | set(current_servers))
    ]
    new_risks = [
        risk
        for entry in entries
        for risk in entry["new_high_or_critical_risks"]
    ]
    new_denies = [
        decision
        for entry in entries
        for decision in entry["new_deny_decisions"]
    ]
    return {
        "schema_version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "baseline": str(baseline_source),
        "current": str(current_source),
        "summary": {
            "added_servers": sum(1 for entry in entries if entry["status"] == "added"),
            "removed_servers": sum(1 for entry in entries if entry["status"] == "removed"),
            "changed_servers": sum(1 for entry in entries if entry["status"] == "changed"),
            "unchanged_servers": sum(1 for entry in entries if entry["status"] == "unchanged"),
            "added_findings": sum(
                len(entry["findings"]["added"]) for entry in entries
            ),
            "removed_findings": sum(
                len(entry["findings"]["removed"]) for entry in entries
            ),
            "changed_findings": sum(
                len(entry["findings"]["changed"]) for entry in entries
            ),
            "added_tool_decisions": sum(
                len(entry["tool_decisions"]["added"]) for entry in entries
            ),
            "removed_tool_decisions": sum(
                len(entry["tool_decisions"]["removed"]) for entry in entries
            ),
            "changed_tool_decisions": sum(
                len(entry["tool_decisions"]["changed"]) for entry in entries
            ),
            "new_high_or_critical_risk": len(new_risks),
            "new_deny_decisions": len(new_denies),
            "gate_failures": {
                "new_high_or_critical_risk": bool(new_risks),
                "new_deny_decisions": bool(new_denies),
            },
        },
        "servers": entries,
    }


def diff_has_new_high_or_critical_risk(diff_report: dict[str, Any]) -> bool:
    return bool(diff_report["summary"]["gate_failures"]["new_high_or_critical_risk"])


def diff_has_new_deny_decision(diff_report: dict[str, Any]) -> bool:
    return bool(diff_report["summary"]["gate_failures"]["new_deny_decisions"])


def write_diff_reports(
    diff_report: dict[str, Any],
    json_path: Path,
    markdown_path: Path,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(diff_report, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_diff_markdown(diff_report), encoding="utf-8")


def render_diff_summary(diff_report: dict[str, Any]) -> str:
    summary = diff_report["summary"]
    return (
        "Diff summary: "
        f"added={summary['added_servers']}, "
        f"removed={summary['removed_servers']}, "
        f"changed={summary['changed_servers']}, "
        f"new_high_or_critical_risk={summary['new_high_or_critical_risk']}, "
        f"new_deny_decisions={summary['new_deny_decisions']}."
    )


def render_diff_markdown(diff_report: dict[str, Any]) -> str:
    summary = diff_report["summary"]
    lines = [
        "# MCP Security Lab Diff",
        "",
        f"Baseline: `{diff_report['baseline']}`",
        f"Current: `{diff_report['current']}`",
        f"Generated: `{diff_report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Added servers: {summary['added_servers']}",
        f"- Removed servers: {summary['removed_servers']}",
        f"- Changed servers: {summary['changed_servers']}",
        f"- New high or critical risk: {summary['new_high_or_critical_risk']}",
        f"- New deny decisions: {summary['new_deny_decisions']}",
        "",
        "## Servers",
        "",
        "| Server | Status | Baseline level | Current level | Added findings | Changed tools | New denies |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for entry in diff_report["servers"]:
        lines.append(
            f"| {_markdown_cell(entry['name'])} | {entry['status']} | "
            f"{entry['baseline']['risk_level'] if entry['baseline'] else 'none'} | "
            f"{entry['current']['risk_level'] if entry['current'] else 'none'} | "
            f"{len(entry['findings']['added'])} | "
            f"{len(entry['tool_decisions']['changed'])} | "
            f"{len(entry['new_deny_decisions'])} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _diff_server(
    name: str,
    baseline: dict[str, Any] | None,
    current: dict[str, Any] | None,
) -> dict[str, Any]:
    findings = _diff_named_items(
        _findings_by_rule(baseline),
        _findings_by_rule(current),
    )
    tool_decisions = _diff_named_items(
        _tools_by_name(baseline),
        _tools_by_name(current),
    )
    entry = {
        "name": name,
        "status": _server_status(baseline, current, findings, tool_decisions),
        "baseline": _server_snapshot(baseline),
        "current": _server_snapshot(current),
        "findings": findings,
        "tool_decisions": tool_decisions,
        "new_high_or_critical_risks": _new_high_or_critical_risks(
            name,
            baseline,
            current,
            findings,
        ),
        "new_deny_decisions": _new_deny_decisions(name, baseline, current),
    }
    return entry


def _server_status(
    baseline: dict[str, Any] | None,
    current: dict[str, Any] | None,
    findings: dict[str, list[Any]],
    tool_decisions: dict[str, list[Any]],
) -> str:
    if baseline is None:
        return "added"
    if current is None:
        return "removed"
    if _server_snapshot(baseline) != _server_snapshot(current):
        return "changed"
    if any(findings[key] for key in ("added", "removed", "changed")):
        return "changed"
    if any(tool_decisions[key] for key in ("added", "removed", "changed")):
        return "changed"
    return "unchanged"


def _servers_by_name(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    servers: dict[str, dict[str, Any]] = {}
    for index, server in enumerate(report.get("servers", []), 1):
        if not isinstance(server, dict):
            continue
        name = str(server.get("name") or f"server-{index}")
        servers[name] = server
    return servers


def _server_snapshot(server: dict[str, Any] | None) -> dict[str, Any] | None:
    if server is None:
        return None
    policy = server.get("policy")
    return {
        "risk_score": server.get("risk_score"),
        "risk_level": server.get("risk_level"),
        "transport": server.get("transport"),
        "read_only": server.get("read_only"),
        "policy_verdict": policy.get("verdict") if isinstance(policy, dict) else None,
    }


def _findings_by_rule(server: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if server is None:
        return {}
    findings: dict[str, dict[str, Any]] = {}
    for index, finding in enumerate(server.get("findings", []), 1):
        if not isinstance(finding, dict):
            continue
        key = str(finding.get("rule_id") or f"finding-{index}")
        findings[key] = finding
    return findings


def _tools_by_name(server: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if server is None:
        return {}
    policy = server.get("policy")
    if not isinstance(policy, dict):
        return {}
    tools: dict[str, dict[str, Any]] = {}
    for index, tool in enumerate(policy.get("tools", []), 1):
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or f"tool-{index}")
        tools[name] = tool
    return tools


def _diff_named_items(
    baseline: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
) -> dict[str, list[Any]]:
    added = [current[key] for key in sorted(set(current) - set(baseline))]
    removed = [baseline[key] for key in sorted(set(baseline) - set(current))]
    changed = [
        {
            "name": key,
            "baseline": baseline[key],
            "current": current[key],
        }
        for key in sorted(set(baseline) & set(current))
        if _canonical(baseline[key]) != _canonical(current[key])
    ]
    return {"added": added, "removed": removed, "changed": changed}


def _new_high_or_critical_risks(
    name: str,
    baseline: dict[str, Any] | None,
    current: dict[str, Any] | None,
    findings: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    if current is None:
        return []
    risks: list[dict[str, Any]] = []
    baseline_level = str(baseline.get("risk_level")) if baseline is not None else None
    current_level = str(current.get("risk_level"))
    if current_level in HIGH_OR_CRITICAL and baseline_level not in HIGH_OR_CRITICAL:
        risks.append(
            {
                "scope": "server",
                "server": name,
                "risk_level": current_level,
                "baseline_risk_level": baseline_level,
            }
        )
    for finding in findings["added"]:
        severity = str(finding.get("severity"))
        if severity in HIGH_OR_CRITICAL:
            risks.append(
                {
                    "scope": "finding",
                    "server": name,
                    "rule_id": finding.get("rule_id"),
                    "severity": severity,
                }
            )
    for changed in findings["changed"]:
        baseline_severity = str(changed["baseline"].get("severity"))
        current_severity = str(changed["current"].get("severity"))
        if current_severity in HIGH_OR_CRITICAL and baseline_severity not in HIGH_OR_CRITICAL:
            risks.append(
                {
                    "scope": "finding",
                    "server": name,
                    "rule_id": changed["current"].get("rule_id"),
                    "severity": current_severity,
                    "baseline_severity": baseline_severity,
                }
            )
    return risks


def _new_deny_decisions(
    name: str,
    baseline: dict[str, Any] | None,
    current: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if current is None:
        return []
    decisions: list[dict[str, Any]] = []
    baseline_policy = baseline.get("policy") if baseline is not None else None
    current_policy = current.get("policy")
    if isinstance(current_policy, dict):
        baseline_verdict = (
            baseline_policy.get("verdict") if isinstance(baseline_policy, dict) else None
        )
        if current_policy.get("verdict") == "deny" and baseline_verdict != "deny":
            decisions.append(
                {
                    "scope": "server",
                    "server": name,
                    "verdict": "deny",
                    "reasons": current_policy.get("reasons", []),
                }
            )
    baseline_tools = _tools_by_name(baseline)
    for tool_name, tool in _tools_by_name(current).items():
        baseline_tool = baseline_tools.get(tool_name)
        baseline_verdict = baseline_tool.get("verdict") if baseline_tool else None
        if tool.get("verdict") == "deny" and baseline_verdict != "deny":
            decisions.append(
                {
                    "scope": "tool",
                    "server": name,
                    "tool": tool_name,
                    "verdict": "deny",
                    "reasons": tool.get("reasons", []),
                }
            )
    return decisions


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")

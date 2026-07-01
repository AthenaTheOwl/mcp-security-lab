from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ServerConfig


VERDICTS = ("allow", "human_approval_required", "deny")
VERDICT_RANK = {"allow": 0, "human_approval_required": 1, "deny": 2}


def load_policy(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required for --policy. Install with `pip install pyyaml`."
        ) from exc

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{path}: cannot read ({exc.strerror})") from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    _validate_policy(data, path)
    return data


def evaluate_policy_for_server(
    policy: dict[str, Any],
    server: ServerConfig,
    scored_server: dict[str, Any],
) -> dict[str, Any]:
    server_rules = _matching_rules(policy.get("server_rules", []), server, scored_server)
    server_verdict = _select_verdict(server_rules, policy.get("server_default", {}), target="server")
    tools = [
        {
            "name": tool["name"],
            **_select_verdict(
                _matching_rules(policy.get("tool_rules", []), server, scored_server, tool=tool),
                policy.get("tool_default", {}),
                target="tool",
            ),
        }
        for tool in _tool_descriptors(server.raw)
    ]
    server_verdict["tools"] = tools
    return server_verdict


def policy_has_deny(report: dict[str, Any]) -> bool:
    for server in report.get("servers", []):
        policy = server.get("policy")
        if not isinstance(policy, dict):
            continue
        if policy.get("verdict") == "deny":
            return True
        for tool in policy.get("tools", []):
            if isinstance(tool, dict) and tool.get("verdict") == "deny":
                return True
    return False


def _validate_policy(policy: dict[str, Any], path: Path) -> None:
    for default_key in ("server_default", "tool_default"):
        value = policy.get(default_key, {})
        if value and not isinstance(value, dict):
            raise ValueError(f"{path}: {default_key} must be a mapping")
        if isinstance(value, dict) and "verdict" in value:
            _validate_verdict(str(value["verdict"]), f"{path}: {default_key}.verdict")

    for rule_group in ("server_rules", "tool_rules"):
        rules = policy.get(rule_group, [])
        if not isinstance(rules, list):
            raise ValueError(f"{path}: {rule_group} must be a list")
        for index, rule in enumerate(rules, 1):
            if not isinstance(rule, dict):
                raise ValueError(f"{path}: {rule_group}[{index}] must be a mapping")
            if not rule.get("id"):
                raise ValueError(f"{path}: {rule_group}[{index}] requires id")
            _validate_verdict(
                str(rule.get("verdict", "")),
                f"{path}: {rule_group}[{index}].verdict",
            )
            match = rule.get("match", {})
            if match and not isinstance(match, dict):
                raise ValueError(f"{path}: {rule_group}[{index}].match must be a mapping")


def _validate_verdict(verdict: str, location: str) -> None:
    if verdict not in VERDICTS:
        raise ValueError(f"{location} must be one of {', '.join(VERDICTS)}")


def _matching_rules(
    rules: Any,
    server: ServerConfig,
    scored_server: dict[str, Any],
    tool: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(rules, list):
        return []
    matches: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        match = rule.get("match", {})
        if not isinstance(match, dict):
            continue
        if _matches(match, server, scored_server, tool):
            matched_findings = _matched_findings(match, scored_server)
            matches.append(
                {
                    "rule_id": str(rule["id"]),
                    "verdict": str(rule["verdict"]),
                    "reason": str(rule.get("reason") or rule["id"]),
                    "matched_findings": matched_findings,
                    "matched_injection_rules": _matched_injection_rules(match, scored_server),
                }
            )
    return matches


def _select_verdict(matches: list[dict[str, Any]], default: Any, target: str) -> dict[str, Any]:
    if not matches:
        default_mapping = default if isinstance(default, dict) else {}
        verdict = str(default_mapping.get("verdict", "allow"))
        _validate_verdict(verdict, f"{target}_default.verdict")
        reason = str(default_mapping.get("reason") or f"No {target} policy rule matched.")
        return {"verdict": verdict, "reasons": [reason], "matched_rules": []}

    selected_rank = max(VERDICT_RANK[match["verdict"]] for match in matches)
    selected = [match for match in matches if VERDICT_RANK[match["verdict"]] == selected_rank]
    return {
        "verdict": selected[0]["verdict"],
        "reasons": [match["reason"] for match in selected],
        "matched_rules": matches,
    }


def _matches(
    match: dict[str, Any],
    server: ServerConfig,
    scored_server: dict[str, Any],
    tool: dict[str, str] | None,
) -> bool:
    finding_ids = set(_finding_ids(scored_server))
    injection_ids = set(_injection_ids(scored_server))

    if "findings_any" in match and not finding_ids.intersection(
        _as_str_list(match["findings_any"])
    ):
        return False
    if "findings_all" in match and not set(_as_str_list(match["findings_all"])).issubset(
        finding_ids
    ):
        return False
    if "findings_none" in match and finding_ids.intersection(
        _as_str_list(match["findings_none"])
    ):
        return False
    if "injection_rules_any" in match and not injection_ids.intersection(
        _as_str_list(match["injection_rules_any"])
    ):
        return False
    if "injection_rules_all" in match and not set(
        _as_str_list(match["injection_rules_all"])
    ).issubset(injection_ids):
        return False
    if "injection_rules_none" in match and injection_ids.intersection(
        _as_str_list(match["injection_rules_none"])
    ):
        return False
    if "risk_levels_any" in match and scored_server.get("risk_level") not in _as_str_list(
        match["risk_levels_any"]
    ):
        return False
    if "risk_score_gte" in match and int(scored_server.get("risk_score", 0)) < int(
        match["risk_score_gte"]
    ):
        return False
    if "transport_any" in match and scored_server.get("transport") not in _as_str_list(
        match["transport_any"]
    ):
        return False
    if "read_only" in match and bool(scored_server.get("read_only")) is not bool(
        match["read_only"]
    ):
        return False

    text = _target_text(server, tool)
    name = tool["name"] if tool else server.name
    if "name_contains_any" in match and not _contains_any(
        name, _as_str_list(match["name_contains_any"])
    ):
        return False
    if "text_contains_any" in match and not _contains_any(
        text, _as_str_list(match["text_contains_any"])
    ):
        return False
    return True


def _matched_findings(match: dict[str, Any], scored_server: dict[str, Any]) -> list[str]:
    finding_ids = set(_finding_ids(scored_server))
    requested: set[str] = set()
    for key in ("findings_any", "findings_all"):
        requested.update(_as_str_list(match.get(key, [])))
    if (
        any(key in match for key in ("injection_rules_any", "injection_rules_all"))
        and "INJECTION-CORPUS" in finding_ids
    ):
        requested.add("INJECTION-CORPUS")
    return sorted(finding_ids.intersection(requested))


def _matched_injection_rules(match: dict[str, Any], scored_server: dict[str, Any]) -> list[str]:
    injection_ids = set(_injection_ids(scored_server))
    requested: set[str] = set()
    for key in ("injection_rules_any", "injection_rules_all"):
        requested.update(_as_str_list(match.get(key, [])))
    return sorted(injection_ids.intersection(requested))


def _finding_ids(scored_server: dict[str, Any]) -> list[str]:
    return [
        str(finding["rule_id"])
        for finding in scored_server.get("findings", [])
        if isinstance(finding, dict) and "rule_id" in finding
    ]


def _injection_ids(scored_server: dict[str, Any]) -> list[str]:
    return [
        str(match["rule_id"])
        for match in scored_server.get("injection_matches", [])
        if isinstance(match, dict) and "rule_id" in match
    ]


def _target_text(server: ServerConfig, tool: dict[str, str] | None) -> str:
    if tool is not None:
        return f"{tool['name']} {tool.get('description', '')}".lower().replace("_", " ")
    return " ".join(_string_values(server.raw)).lower().replace("_", " ")


def _tool_descriptors(raw: dict[str, Any]) -> list[dict[str, str]]:
    tools = raw.get("tools") or raw.get("toolDescriptors") or []
    descriptors: list[dict[str, str]] = []
    if isinstance(tools, list):
        for index, tool in enumerate(tools, 1):
            descriptors.append(_coerce_tool(tool, fallback_name=f"tool-{index}"))
    elif isinstance(tools, dict):
        for name, tool in tools.items():
            descriptors.append(_coerce_tool(tool, fallback_name=str(name)))
    return descriptors


def _coerce_tool(tool: Any, fallback_name: str) -> dict[str, str]:
    if isinstance(tool, str):
        return {"name": tool, "description": ""}
    if isinstance(tool, dict):
        name = str(tool.get("name") or tool.get("id") or fallback_name)
        description = str(tool.get("description") or tool.get("title") or tool.get("prompt") or "")
        return {"name": name, "description": description}
    return {"name": fallback_name, "description": ""}


def _contains_any(text: str, needles: list[str]) -> bool:
    normalized = text.lower().replace("_", " ")
    return any(needle.lower().replace("_", " ") in normalized for needle in needles)


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values: list[str] = []
        for key, item in value.items():
            values.append(str(key))
            values.extend(_string_values(item))
        return values
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(_string_values(item))
        return values
    return []

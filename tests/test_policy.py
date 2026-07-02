from __future__ import annotations

import json
from pathlib import Path

from mcp_security_lab.cli import main
from mcp_security_lab.config import ServerConfig, load_servers
from mcp_security_lab.policy import evaluate_policy_for_server, load_policy, policy_has_deny
from mcp_security_lab.report import build_report, render_markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "examples" / "policies" / "default.yaml"
FIXTURES = ROOT / "tests" / "fixtures"


def test_default_policy_denies_broad_local_shell() -> None:
    policy = load_policy(DEFAULT_POLICY)
    servers = load_servers(ROOT / "examples" / "risky-filesystem-shell-server.json")
    report = build_report(
        servers,
        source=Path("risky.json"),
        policy=policy,
        policy_source=DEFAULT_POLICY,
    )

    server_policy = report["servers"][0]["policy"]
    assert server_policy["verdict"] == "deny"
    assert "INJECTION-CORPUS" in _matched_findings(server_policy)
    assert {tool["name"]: tool["verdict"] for tool in server_policy["tools"]} == {
        "write_file": "deny",
        "run_shell": "deny",
    }
    assert policy_has_deny(report) is True


def test_policy_fixture_verdicts_cover_required_server_shapes() -> None:
    policy = load_policy(DEFAULT_POLICY)

    cases = {
        "local-shell-server.json": ("human_approval_required", {"run_shell": "deny"}),
        "broad-filesystem-server.json": ("human_approval_required", {"write_file": "deny"}),
        "remote-unauthenticated-server.json": (
            "human_approval_required",
            {"fetch_ticket": "human_approval_required"},
        ),
        "readonly-resource-server.json": ("allow", {"read_doc": "allow"}),
    }
    for filename, expected in cases.items():
        servers = load_servers(FIXTURES / filename)
        report = build_report(
            servers,
            source=Path(filename),
            policy=policy,
            policy_source=DEFAULT_POLICY,
        )
        server_policy = report["servers"][0]["policy"]
        assert server_policy["verdict"] == expected[0]
        assert {tool["name"]: tool["verdict"] for tool in server_policy["tools"]} == expected[1]


def test_policy_report_json_and_markdown_shapes() -> None:
    policy = load_policy(DEFAULT_POLICY)
    servers = load_servers(ROOT / "examples" / "remote-unauthenticated-server.json")
    report = build_report(
        servers,
        source=Path("remote.json"),
        policy=policy,
        policy_source=DEFAULT_POLICY,
    )
    markdown = render_markdown(report)

    assert report["policy"]["verdict_counts"]["human_approval_required"] == 1
    assert report["servers"][0]["policy"]["reasons"] == ["Remote transport lacks auth metadata."]
    assert "## Policy" in markdown
    assert "| remote-ticket-tools | `human_approval_required` |" in markdown


def test_cli_fail_on_deny_returns_nonzero_and_writes_report(tmp_path) -> None:
    report_path = tmp_path / "report.json"

    result = main(
        [
            "scan",
            str(ROOT / "examples" / "risky-filesystem-shell-server.json"),
            "--policy",
            str(DEFAULT_POLICY),
            "--fail-on-deny",
            "--out",
            str(report_path),
        ]
    )

    assert result == 1
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["servers"][0]["policy"]["verdict"] == "deny"
    assert report_path.with_suffix(".md").is_file()


def _scored(**overrides: object) -> dict[str, object]:
    scored: dict[str, object] = {
        "risk_score": 0,
        "risk_level": "low",
        "transport": "stdio",
        "read_only": False,
        "findings": [],
        "injection_matches": [],
    }
    scored.update(overrides)
    return scored


def _evaluate(rule_match: dict[str, object], default_verdict: str, scored: dict[str, object]) -> str:
    policy = {
        "server_rules": [
            {"id": "rule", "verdict": "deny", "reason": "matched", "match": rule_match}
        ],
        "server_default": {"verdict": default_verdict, "reason": "default"},
    }
    server = ServerConfig("s", {"tools": []})
    return evaluate_policy_for_server(policy, server, scored)["verdict"]


def test_risk_score_gte_matcher_boundary() -> None:
    # risk_score_gte is unused in default.yaml; pin the >= boundary directly.
    match = {"risk_score_gte": 50}
    assert _evaluate(match, "allow", _scored(risk_score=49)) == "allow"
    assert _evaluate(match, "allow", _scored(risk_score=50)) == "deny"


def test_findings_none_matcher_blocks_on_listed_finding() -> None:
    # findings_none must veto the match when a listed finding is present,
    # independent of any co-located read_only guard.
    match = {"findings_none": ["STDIO-COMMAND"]}
    clean = _scored(findings=[])
    dirty = _scored(findings=[{"rule_id": "STDIO-COMMAND"}])
    assert _evaluate(match, "allow", clean) == "deny"
    assert _evaluate(match, "allow", dirty) == "allow"


def test_read_only_matcher_distinguishes_read_only_servers() -> None:
    # read_only:true must match a read-only server and not a writable one.
    match = {"read_only": True}
    assert _evaluate(match, "allow", _scored(read_only=True)) == "deny"
    assert _evaluate(match, "allow", _scored(read_only=False)) == "allow"


def _matched_findings(policy_result: dict[str, object]) -> set[str]:
    matched: set[str] = set()
    for rule in policy_result["matched_rules"]:  # type: ignore[index]
        if isinstance(rule, dict):
            matched.update(str(item) for item in rule.get("matched_findings", []))
    return matched

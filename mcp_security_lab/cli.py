from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_servers
from .diff import (
    build_diff_report,
    diff_has_new_deny_decision,
    diff_has_new_high_or_critical_risk,
    load_report,
    render_diff_summary,
    write_diff_reports,
)
from .policy import load_policy, policy_has_deny
from .report import build_report, render_show, write_reports

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHOW_REPORT = REPO_ROOT / "reports" / "example.json"
DEFAULT_SHOW_CONFIG = REPO_ROOT / "examples" / "claude-desktop-config.json"
DEFAULT_SHOW_POLICY = REPO_ROOT / "examples" / "policies" / "default.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcp_security_lab")
    subcommands = parser.add_subparsers(dest="command", required=True)

    scan = subcommands.add_parser("scan", help="scan an MCP server config")
    scan.add_argument("config", type=Path, help="path to a JSON MCP config")
    scan.add_argument("--out", type=Path, required=True, help="JSON report path")
    scan.add_argument("--policy", type=Path, default=None, help="YAML policy file to evaluate")
    scan.add_argument(
        "--fail-on-deny",
        action="store_true",
        help="exit nonzero when the evaluated policy returns deny",
    )
    scan.add_argument(
        "--markdown",
        type=Path,
        default=None,
        help="Markdown report path; defaults to the JSON path with .md suffix",
    )

    show = subcommands.add_parser(
        "show",
        help="print a ranked, human-readable summary of a committed report",
    )
    show.add_argument(
        "report",
        type=Path,
        nargs="?",
        default=DEFAULT_SHOW_REPORT,
        help="JSON report path (defaults to the committed example report)",
    )

    diff = subcommands.add_parser("diff", help="compare two MCP Security Lab JSON reports")
    diff.add_argument("--baseline", type=Path, required=True, help="baseline JSON report path")
    diff.add_argument("--current", type=Path, required=True, help="current JSON report path")
    diff.add_argument("--out", type=Path, required=True, help="JSON diff report path")
    diff.add_argument(
        "--markdown",
        type=Path,
        default=None,
        help="Markdown diff path; defaults to the JSON path with .md suffix",
    )
    diff.add_argument(
        "--fail-on-new-critical",
        "--fail-on-new-high-critical",
        dest="fail_on_new_critical",
        action="store_true",
        help="exit nonzero when current introduces new high or critical risk",
    )
    diff.add_argument(
        "--fail-on-new-deny",
        action="store_true",
        help="exit nonzero when current introduces a new policy deny decision",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        servers = load_servers(args.config)
        policy = load_policy(args.policy) if args.policy else None
        report = build_report(servers, args.config, policy=policy, policy_source=args.policy)
        markdown_path = args.markdown or args.out.with_suffix(".md")
        write_reports(report, args.out, markdown_path)
        print(f"Wrote {args.out} and {markdown_path}")
        if args.fail_on_deny and policy is not None and policy_has_deny(report):
            print("Policy denied at least one server or tool.")
            return 1
        return 0

    if args.command == "show":
        import json

        report_path = Path(args.report)
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
        elif report_path == DEFAULT_SHOW_REPORT and DEFAULT_SHOW_CONFIG.exists():
            policy = load_policy(DEFAULT_SHOW_POLICY) if DEFAULT_SHOW_POLICY.exists() else None
            report = build_report(
                load_servers(DEFAULT_SHOW_CONFIG),
                DEFAULT_SHOW_CONFIG,
                policy=policy,
                policy_source=DEFAULT_SHOW_POLICY if policy is not None else None,
            )
        else:
            raise FileNotFoundError(report_path)
        print(render_show(report), end="")
        return 0

    if args.command == "diff":
        baseline = load_report(args.baseline)
        current = load_report(args.current)
        diff_report = build_diff_report(baseline, current, args.baseline, args.current)
        markdown_path = args.markdown or args.out.with_suffix(".md")
        write_diff_reports(diff_report, args.out, markdown_path)
        print(f"Wrote {args.out} and {markdown_path}")
        print(render_diff_summary(diff_report))
        should_fail = (
            args.fail_on_new_critical
            and diff_has_new_high_or_critical_risk(diff_report)
        ) or (
            args.fail_on_new_deny
            and diff_has_new_deny_decision(diff_report)
        )
        if should_fail:
            return 1
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_servers
from .policy import load_policy, policy_has_deny
from .report import build_report, write_reports


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

    parser.error(f"unknown command: {args.command}")
    return 2

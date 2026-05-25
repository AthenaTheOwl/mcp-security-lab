from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_servers
from .report import build_report, write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcp_security_lab")
    subcommands = parser.add_subparsers(dest="command", required=True)

    scan = subcommands.add_parser("scan", help="scan an MCP server config")
    scan.add_argument("config", type=Path, help="path to a JSON MCP config")
    scan.add_argument("--out", type=Path, required=True, help="JSON report path")
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
        report = build_report(servers, args.config)
        markdown_path = args.markdown or args.out.with_suffix(".md")
        write_reports(report, args.out, markdown_path)
        print(f"Wrote {args.out} and {markdown_path}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


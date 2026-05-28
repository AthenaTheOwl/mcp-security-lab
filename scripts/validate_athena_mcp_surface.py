"""Validate athena-site MCP server tool-surface against its committed snapshot.

This is the Phase E drift gate. The athena-mcp-server commits a
`tool-surface.snapshot.json` describing the exact set of tools it exposes plus
a SHA-256 of each tool's canonical input schema. This gate regenerates the
snapshot from the live source and compares it to the committed copy. Any
added, removed, or changed tool is drift; the gate exits 1 with a structured
JSON report under `reports/`.

Live-surface acquisition strategy (whichever is reliable wins):

1. If `ATHENA_SITE_MCP_LIVE_SNAPSHOT` env var is set, treat that as a path
   to a JSON file already containing the live surface (CI seam, test seam).
2. If `ATHENA_SITE_REPO` env var is set, run
   `npm --prefix $ATHENA_SITE_REPO/apps/mcp-server run --silent snapshot`
   into a temp file. The npm script writes
   `tool-surface.snapshot.json`; we copy it to a temp path and read it.
3. If neither is set and `../athena-site` is a sibling directory of this
   repo, use that.

Exit codes:
  0  surfaces match
  1  drift detected; report under reports/mcp-surface-diff.json
  2  gate misconfiguration (snapshot missing, live source unreachable)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_DIR = ROOT / "reports"
DEFAULT_REPORT_PATH = DEFAULT_REPORTS_DIR / "mcp-surface-diff.json"
SCHEMA_VERSION = "0.1.0"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare athena-mcp-server's committed tool surface against the live source.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Path to the committed tool-surface.snapshot.json (defaults to the sibling athena-site repo).",
    )
    parser.add_argument(
        "--live",
        type=Path,
        help="Path to a pre-built live tool-surface JSON file (skips the npm regeneration step).",
    )
    parser.add_argument(
        "--athena-site-repo",
        type=Path,
        help="Override path to the athena-site repo root (otherwise inferred from env or sibling).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Where to write the diff report (default: reports/mcp-surface-diff.json).",
    )
    args = parser.parse_args(argv)

    snapshot_path = resolve_snapshot_path(args)
    if snapshot_path is None or not snapshot_path.is_file():
        print(
            "validate_athena_mcp_surface: committed snapshot not found. "
            f"Looked at: {snapshot_path}",
            file=sys.stderr,
        )
        return 2

    try:
        snapshot = load_snapshot(snapshot_path)
    except ValueError as exc:
        print(f"validate_athena_mcp_surface: invalid snapshot at {snapshot_path}: {exc}", file=sys.stderr)
        return 2

    live_source_label: str
    try:
        live, live_source_label = obtain_live_surface(args, snapshot_path)
    except RuntimeError as exc:
        print(f"validate_athena_mcp_surface: {exc}", file=sys.stderr)
        return 2

    report = build_diff_report(
        snapshot=snapshot,
        live=live,
        snapshot_path=snapshot_path,
        live_source=live_source_label,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if report["drift_detected"]:
        print(render_summary(report), file=sys.stderr)
        return 1
    print(f"validate_athena_mcp_surface OK ({report['summary']['unchanged']} tools matched)")
    return 0


def resolve_snapshot_path(args: argparse.Namespace) -> Path | None:
    if args.snapshot is not None:
        return args.snapshot.resolve()
    athena = resolve_athena_site(args)
    if athena is None:
        return None
    return (athena / "apps" / "mcp-server" / "tool-surface.snapshot.json").resolve()


def resolve_athena_site(args: argparse.Namespace) -> Path | None:
    if args.athena_site_repo is not None:
        return args.athena_site_repo.resolve()
    env_repo = os.environ.get("ATHENA_SITE_REPO")
    if env_repo:
        return Path(env_repo).resolve()
    sibling = (ROOT / ".." / "athena-site").resolve()
    if sibling.is_dir():
        return sibling
    return None


def obtain_live_surface(
    args: argparse.Namespace,
    snapshot_path: Path,
) -> tuple[dict[str, Any], str]:
    # Strategy 1: explicit --live or env override.
    env_live = os.environ.get("ATHENA_SITE_MCP_LIVE_SNAPSHOT")
    if args.live is not None:
        return load_snapshot(args.live.resolve()), f"file:{args.live.resolve()}"
    if env_live:
        return load_snapshot(Path(env_live).resolve()), f"env:ATHENA_SITE_MCP_LIVE_SNAPSHOT={env_live}"

    # Strategy 2: regenerate via npm into a temp file.
    athena = resolve_athena_site(args)
    if athena is None:
        raise RuntimeError(
            "no live source. Pass --live, set ATHENA_SITE_MCP_LIVE_SNAPSHOT, "
            "or place athena-site as a sibling of this repo."
        )
    mcp_server_dir = athena / "apps" / "mcp-server"
    if not mcp_server_dir.is_dir():
        raise RuntimeError(
            f"athena-site repo at {athena} has no apps/mcp-server/ directory."
        )

    # Run the npm snapshot script into a copy. The script writes the file at
    # apps/mcp-server/tool-surface.snapshot.json; we back the existing copy
    # up, run, copy aside, restore.
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm not on PATH; cannot regenerate live snapshot.")

    snapshot_file = mcp_server_dir / "tool-surface.snapshot.json"
    backup_text = snapshot_file.read_text(encoding="utf-8") if snapshot_file.is_file() else None
    try:
        result = subprocess.run(
            [npm, "run", "--silent", "snapshot"],
            cwd=mcp_server_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "npm run snapshot failed in "
                f"{mcp_server_dir} (exit {result.returncode}): {result.stderr.strip()}"
            )
        if not snapshot_file.is_file():
            raise RuntimeError(
                f"snapshot script did not write {snapshot_file}"
            )
        live = json.loads(snapshot_file.read_text(encoding="utf-8"))
    finally:
        # Always restore the committed snapshot byte-for-byte so this gate is
        # non-destructive. The snapshot script is deterministic so this
        # round-trip is normally identical, but we restore unconditionally.
        if backup_text is not None:
            snapshot_file.write_text(backup_text, encoding="utf-8")

    return live, f"npm:snapshot@{mcp_server_dir}"


def load_snapshot(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("top-level value must be an object")
    if not isinstance(data.get("tools"), list):
        raise ValueError("'tools' must be an array")
    for entry in data["tools"]:
        if not isinstance(entry, dict):
            raise ValueError("'tools' entries must be objects")
        if not isinstance(entry.get("name"), str):
            raise ValueError("'tools' entries must have a string name")
        if not isinstance(entry.get("input_schema_hash"), str):
            raise ValueError("'tools' entries must have a string input_schema_hash")
    return data


def build_diff_report(
    snapshot: dict[str, Any],
    live: dict[str, Any],
    snapshot_path: Path,
    live_source: str,
) -> dict[str, Any]:
    snapshot_tools = {t["name"]: t for t in snapshot.get("tools", []) if isinstance(t, dict)}
    live_tools = {t["name"]: t for t in live.get("tools", []) if isinstance(t, dict)}

    added_names = sorted(set(live_tools) - set(snapshot_tools))
    removed_names = sorted(set(snapshot_tools) - set(live_tools))
    common = sorted(set(snapshot_tools) & set(live_tools))

    added = [tool_entry(live_tools[n]) for n in added_names]
    removed = [tool_entry(snapshot_tools[n]) for n in removed_names]
    changed: list[dict[str, Any]] = []
    unchanged_count = 0
    for name in common:
        snap = snapshot_tools[name]
        liv = live_tools[name]
        if snap.get("input_schema_hash") != liv.get("input_schema_hash") or snap.get("description") != liv.get("description"):
            changed.append({
                "name": name,
                "snapshot": tool_entry(snap, include_name=False),
                "live": tool_entry(liv, include_name=False),
            })
        else:
            unchanged_count += 1

    drift = bool(added) or bool(removed) or bool(changed)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "snapshot_path": str(snapshot_path),
        "live_source": live_source,
        "drift_detected": drift,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": unchanged_count,
        },
        "added_tools": added,
        "removed_tools": removed,
        "changed_tools": changed,
    }


def tool_entry(entry: dict[str, Any], include_name: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if include_name:
        out["name"] = entry.get("name", "")
    if "description" in entry:
        out["description"] = entry["description"]
    out["input_schema_hash"] = entry.get("input_schema_hash", "")
    return out


def render_summary(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "validate_athena_mcp_surface: DRIFT detected.",
        f"  snapshot: {report['snapshot_path']}",
        f"  live:     {report['live_source']}",
        f"  added={summary['added']} removed={summary['removed']} "
        f"changed={summary['changed']} unchanged={summary['unchanged']}",
    ]
    for tool in report["added_tools"]:
        lines.append(f"  + added: {tool['name']}")
    for tool in report["removed_tools"]:
        lines.append(f"  - removed: {tool['name']}")
    for tool in report["changed_tools"]:
        lines.append(
            f"  ~ changed: {tool['name']} "
            f"(snapshot={tool['snapshot']['input_schema_hash'][:12]}... -> "
            f"live={tool['live']['input_schema_hash'][:12]}...)"
        )
    return "\n".join(lines)


# Re-export load_snapshot / build_diff_report under their canonical names so
# tests can call them directly without re-implementing the wiring.
__all__: Iterable[str] = (
    "build_diff_report",
    "load_snapshot",
    "main",
    "render_summary",
)


if __name__ == "__main__":
    sys.exit(main())

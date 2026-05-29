"""Validate one or all registered MCP servers' tool surfaces against their
committed snapshots.

This is the Phase E drift gate, parameterized. Each MCP server enrolled in
`config/mcp_server_registry.yaml` declares its repo, server path, snapshot
path, and regeneration command. The gate looks up the entry (or iterates all
enabled entries), regenerates the live surface, and compares it tool-by-tool
to the committed snapshot. Any added, removed, or changed tool is drift; the
gate exits 1 with a structured JSON report per server under `reports/`.

Live-surface acquisition strategy (whichever wins, per server):

1. If `<ID_UPPER>_LIVE_SNAPSHOT` env var is set (e.g. for
   athena-portfolio-query: `ATHENA_PORTFOLIO_QUERY_LIVE_SNAPSHOT`), treat it
   as a path to a JSON file already containing the live surface.
2. Resolve the server's repo root:
   - `<ID_UPPER>_REPO` env var (e.g. `ATHENA_PORTFOLIO_QUERY_REPO`)
   - legacy alias `<LEGACY_REPO_UPPER>_REPO` for
     athena-site (`ATHENA_SITE_REPO`)
   - sibling directory `../<repo>` next to this lab repo
3. Run the per-server `snapshot_script` inside `<repo>/<server_path>`. The
   script writes the snapshot back at `<repo>/<snapshot_path>`; the gate
   backs that file up byte-for-byte, runs, reads the regenerated file, and
   restores the backup so the gate is non-destructive.

Exit codes:
  0  all gated surfaces match
  1  at least one server's surface drifted
  2  gate misconfiguration (registry malformed, snapshot missing, live
     source unreachable, npm not on PATH, etc.)

Invocation:
  python scripts/validate_mcp_surface.py                # gate every enabled
  python scripts/validate_mcp_surface.py --all          # same as above
  python scripts/validate_mcp_surface.py --server-id athena-portfolio-query
  python scripts/validate_mcp_surface.py --snapshot <path> --live <path>
    # ad-hoc compare (no registry lookup), legacy single-server mode

Reports land at:
  reports/mcp-surface-diff.<server-id>.json   per-server diff report
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_DIR = ROOT / "reports"
DEFAULT_REGISTRY_PATH = ROOT / "config" / "mcp_server_registry.yaml"
SCHEMA_VERSION = "0.1.0"

# Legacy env-var alias map: older invocations used ATHENA_SITE_REPO directly
# for the athena-portfolio-query server. We honor the original name in
# addition to the new ID-based convention.
LEGACY_REPO_ENV_ALIASES: dict[str, str] = {
    "athena-portfolio-query": "ATHENA_SITE_REPO",
}
LEGACY_LIVE_ENV_ALIASES: dict[str, str] = {
    "athena-portfolio-query": "ATHENA_SITE_MCP_LIVE_SNAPSHOT",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare each registered MCP server's committed tool surface "
            "against the live source. With no flags, gates every enabled "
            "server in the registry."
        ),
    )
    parser.add_argument(
        "--server-id",
        type=str,
        help="Gate a single server by registry id (e.g. athena-portfolio-query).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Gate every enabled server in the registry (default when no flag is passed).",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Path to the MCP server registry YAML (default: config/mcp_server_registry.yaml).",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Ad-hoc: path to a committed tool-surface.snapshot.json (bypasses registry).",
    )
    parser.add_argument(
        "--live",
        type=Path,
        help="Ad-hoc: path to a pre-built live tool-surface JSON file (bypasses npm regeneration).",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help="Directory where per-server diff reports are written (default: reports/).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Ad-hoc: explicit single-report output path (only used with --snapshot/--live).",
    )
    # Legacy --athena-site-repo flag preserved for back-compat with the
    # original validate_athena_mcp_surface.py CLI contract.
    parser.add_argument(
        "--athena-site-repo",
        type=Path,
        help="Legacy override: path to the athena-site repo root.",
    )
    args = parser.parse_args(argv)

    # Ad-hoc mode: explicit --snapshot/--live, no registry lookup. Preserves
    # the original single-server CLI contract for tests and one-off runs.
    if args.snapshot is not None or args.live is not None:
        return _run_adhoc(args)

    # Registry mode.
    try:
        registry = load_registry(args.registry)
    except RegistryError as exc:
        print(f"validate_mcp_surface: registry error: {exc}", file=sys.stderr)
        return 2

    if args.server_id:
        matches = [s for s in registry if s["id"] == args.server_id]
        if not matches:
            print(
                f"validate_mcp_surface: --server-id {args.server_id!r} "
                f"not found in {args.registry}",
                file=sys.stderr,
            )
            return 2
        servers = matches
    else:
        # Default: every enabled server.
        servers = [s for s in registry if s.get("enabled", True)]
        if not servers:
            print(
                "validate_mcp_surface: no enabled servers in registry; nothing to gate.",
                file=sys.stderr,
            )
            return 0

    args.reports_dir.mkdir(parents=True, exist_ok=True)

    any_drift = False
    any_error = False
    for server in servers:
        sid = server["id"]
        out_path = args.reports_dir / f"mcp-surface-diff.{sid}.json"
        try:
            drift = _gate_one_server(
                server=server,
                out_path=out_path,
                cli_athena_override=args.athena_site_repo,
            )
        except GateMisconfigured as exc:
            print(f"validate_mcp_surface[{sid}]: {exc}", file=sys.stderr)
            any_error = True
            continue
        if drift:
            any_drift = True

    if any_error:
        return 2
    if any_drift:
        return 1
    return 0


class RegistryError(Exception):
    """Raised when the MCP server registry file is missing or malformed."""


class GateMisconfigured(Exception):
    """Raised when a single server's gate cannot run (missing snapshot, etc.)."""


def load_registry(path: Path) -> list[dict[str, Any]]:
    """Parse and validate the MCP server registry YAML."""
    if not path.is_file():
        raise RegistryError(f"registry file not found at {path}")
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RegistryError(
            "PyYAML is required to load the registry. Install with `pip install pyyaml`."
        ) from exc
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RegistryError(f"YAML parse error in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError(f"top-level YAML must be a mapping in {path}")
    if data.get("version") != 1:
        raise RegistryError(
            f"unsupported registry version {data.get('version')!r} in {path}; expected 1"
        )
    servers = data.get("servers")
    if not isinstance(servers, list) or not servers:
        raise RegistryError(f"`servers` must be a non-empty array in {path}")

    required_fields = (
        "id",
        "name",
        "repo",
        "server_path",
        "snapshot_path",
        "snapshot_script",
        "runtime",
    )
    seen_ids: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    for index, entry in enumerate(servers):
        if not isinstance(entry, dict):
            raise RegistryError(f"servers[{index}] must be a mapping in {path}")
        for field in required_fields:
            if field not in entry or not isinstance(entry[field], str) or not entry[field].strip():
                raise RegistryError(
                    f"servers[{index}] missing required string field {field!r} in {path}"
                )
        if "enabled" in entry and not isinstance(entry["enabled"], bool):
            raise RegistryError(
                f"servers[{index}] field 'enabled' must be boolean in {path}"
            )
        sid = entry["id"]
        if sid in seen_ids:
            raise RegistryError(f"duplicate server id {sid!r} in {path}")
        seen_ids.add(sid)
        cleaned.append(entry)
    return cleaned


def _gate_one_server(
    server: dict[str, Any],
    out_path: Path,
    cli_athena_override: Path | None,
) -> bool:
    """Gate a single server. Returns True if drift was detected.

    Raises GateMisconfigured if the gate cannot run for this server.
    """
    sid = server["id"]
    snapshot_path = resolve_snapshot_path_for_server(server, cli_athena_override)
    if snapshot_path is None or not snapshot_path.is_file():
        raise GateMisconfigured(
            f"committed snapshot not found. Looked at: {snapshot_path}"
        )
    try:
        snapshot = load_snapshot(snapshot_path)
    except ValueError as exc:
        raise GateMisconfigured(f"invalid snapshot at {snapshot_path}: {exc}") from exc

    try:
        live, live_source_label = obtain_live_surface_for_server(
            server, snapshot_path, cli_athena_override
        )
    except RuntimeError as exc:
        raise GateMisconfigured(str(exc)) from exc

    report = build_diff_report(
        snapshot=snapshot,
        live=live,
        snapshot_path=snapshot_path,
        live_source=live_source_label,
        server_id=sid,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if report["drift_detected"]:
        print(render_summary(report), file=sys.stderr)
        return True
    print(f"validate_mcp_surface[{sid}] OK ({report['summary']['unchanged']} tools matched)")
    return False


def _run_adhoc(args: argparse.Namespace) -> int:
    """Original single-server CLI: explicit --snapshot/--live paths.

    Preserves the contract that validate_athena_mcp_surface.py exposed before
    the registry refactor: callers can still pass exact files for unit tests
    or one-off comparisons without touching the registry.
    """
    if args.snapshot is None:
        print(
            "validate_mcp_surface: --live requires --snapshot in ad-hoc mode.",
            file=sys.stderr,
        )
        return 2
    snapshot_path = args.snapshot.resolve()
    if not snapshot_path.is_file():
        print(
            f"validate_mcp_surface: committed snapshot not found. Looked at: {snapshot_path}",
            file=sys.stderr,
        )
        return 2
    try:
        snapshot = load_snapshot(snapshot_path)
    except ValueError as exc:
        print(
            f"validate_mcp_surface: invalid snapshot at {snapshot_path}: {exc}",
            file=sys.stderr,
        )
        return 2

    if args.live is None:
        print(
            "validate_mcp_surface: ad-hoc mode requires --live (no registry lookup).",
            file=sys.stderr,
        )
        return 2
    try:
        live = load_snapshot(args.live.resolve())
    except ValueError as exc:
        print(
            f"validate_mcp_surface: invalid live snapshot at {args.live}: {exc}",
            file=sys.stderr,
        )
        return 2
    live_source_label = f"file:{args.live.resolve()}"

    out_path = args.out if args.out else DEFAULT_REPORTS_DIR / "mcp-surface-diff.json"
    report = build_diff_report(
        snapshot=snapshot,
        live=live,
        snapshot_path=snapshot_path,
        live_source=live_source_label,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if report["drift_detected"]:
        print(render_summary(report), file=sys.stderr)
        return 1
    print(f"validate_mcp_surface OK ({report['summary']['unchanged']} tools matched)")
    return 0


def resolve_snapshot_path_for_server(
    server: dict[str, Any],
    cli_athena_override: Path | None,
) -> Path | None:
    repo_root = resolve_repo_root_for_server(server, cli_athena_override)
    if repo_root is None:
        return None
    return (repo_root / server["snapshot_path"]).resolve()


def resolve_repo_root_for_server(
    server: dict[str, Any],
    cli_athena_override: Path | None,
) -> Path | None:
    sid = server["id"]
    repo_dirname = server["repo"]

    # Legacy CLI flag still wins for the athena-portfolio-query server.
    if sid == "athena-portfolio-query" and cli_athena_override is not None:
        return cli_athena_override.resolve()

    # Per-server env var: id "athena-portfolio-query" ->
    # ATHENA_PORTFOLIO_QUERY_REPO.
    env_var = _id_to_env_prefix(sid) + "_REPO"
    env_repo = os.environ.get(env_var)
    if env_repo:
        return Path(env_repo).resolve()

    # Legacy alias (preserves the original ATHENA_SITE_REPO contract).
    legacy_env = LEGACY_REPO_ENV_ALIASES.get(sid)
    if legacy_env:
        legacy_value = os.environ.get(legacy_env)
        if legacy_value:
            return Path(legacy_value).resolve()

    # Sibling directory fallback: ../<repo> next to this lab.
    sibling = (ROOT / ".." / repo_dirname).resolve()
    if sibling.is_dir():
        return sibling
    return None


def obtain_live_surface_for_server(
    server: dict[str, Any],
    snapshot_path: Path,
    cli_athena_override: Path | None,
) -> tuple[dict[str, Any], str]:
    sid = server["id"]

    # Strategy 1: env-var live-snapshot override.
    env_var = _id_to_env_prefix(sid) + "_LIVE_SNAPSHOT"
    env_live = os.environ.get(env_var)
    if env_live:
        return load_snapshot(Path(env_live).resolve()), f"env:{env_var}={env_live}"

    legacy_live_env = LEGACY_LIVE_ENV_ALIASES.get(sid)
    if legacy_live_env:
        legacy_live_value = os.environ.get(legacy_live_env)
        if legacy_live_value:
            return (
                load_snapshot(Path(legacy_live_value).resolve()),
                f"env:{legacy_live_env}={legacy_live_value}",
            )

    # Strategy 2: regenerate via the per-server snapshot script.
    repo_root = resolve_repo_root_for_server(server, cli_athena_override)
    if repo_root is None:
        raise RuntimeError(
            f"no live source for {sid}. Set {env_var}, configure {env_var[:-len('_LIVE_SNAPSHOT')]}_REPO, "
            f"or place {server['repo']} as a sibling of this repo."
        )
    server_dir = (repo_root / server["server_path"]).resolve()
    if not server_dir.is_dir():
        raise RuntimeError(
            f"server source directory missing for {sid}: {server_dir}"
        )

    snapshot_file = (repo_root / server["snapshot_path"]).resolve()
    cmd_parts = server["snapshot_script"].split()
    if not cmd_parts:
        raise RuntimeError(f"empty snapshot_script for {sid}")
    exe = cmd_parts[0]
    resolved_exe = shutil.which(exe)
    if resolved_exe is None:
        raise RuntimeError(
            f"snapshot_script binary {exe!r} not on PATH; cannot regenerate live snapshot for {sid}."
        )

    # Use binary I/O for the backup+restore pair so the round-trip is
    # byte-perfect. Text-mode read_text/write_text performs CRLF<->LF
    # translation on Windows, which would leave the LF-committed snapshot
    # file dirty after every gate run. The intermediate JSON load below
    # stays text-mode because JSON is whitespace-insensitive.
    backup_bytes = snapshot_file.read_bytes() if snapshot_file.is_file() else None
    try:
        full_cmd = [resolved_exe, *cmd_parts[1:]]
        result = subprocess.run(
            full_cmd,
            cwd=server_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"snapshot_script failed in {server_dir} (exit {result.returncode}): "
                f"{result.stderr.strip()}"
            )
        if not snapshot_file.is_file():
            raise RuntimeError(f"snapshot_script did not write {snapshot_file}")
        live = json.loads(snapshot_file.read_text(encoding="utf-8"))
    finally:
        if backup_bytes is not None:
            snapshot_file.write_bytes(backup_bytes)

    return live, f"script:{server['snapshot_script']}@{server_dir}"


def _id_to_env_prefix(server_id: str) -> str:
    """Convert a registry id (kebab-case) into an env-var prefix.

    "athena-portfolio-query" -> "ATHENA_PORTFOLIO_QUERY".
    """
    return server_id.replace("-", "_").upper()


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
    server_id: str | None = None,
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

    report: dict[str, Any] = {
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
    if server_id is not None:
        report["server_id"] = server_id
    return report


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
    sid = report.get("server_id", "")
    header_suffix = f"[{sid}]" if sid else ""
    lines = [
        f"validate_mcp_surface{header_suffix}: DRIFT detected.",
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


__all__: Iterable[str] = (
    "GateMisconfigured",
    "RegistryError",
    "build_diff_report",
    "load_registry",
    "load_snapshot",
    "main",
    "obtain_live_surface_for_server",
    "render_summary",
    "resolve_repo_root_for_server",
    "resolve_snapshot_path_for_server",
)


if __name__ == "__main__":
    sys.exit(main())

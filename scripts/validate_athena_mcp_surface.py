"""Legacy alias for validate_mcp_surface.py.

DEC-MCPSEC-008 parameterized the drift gate over an MCP server registry. The
gate logic lives in `scripts/validate_mcp_surface.py`; this file preserves
the original entrypoint so anyone (tests, ad-hoc invocations, docs) that
referred to `validate_athena_mcp_surface.py` keeps working.

For the registry-aware default behaviour (gate every enabled server), call
`scripts/validate_mcp_surface.py` directly. This alias still exposes the
single-server CLI contract: `--snapshot` + `--live` for ad-hoc compares,
`--athena-site-repo` legacy override, etc. With no flags, it pins to the
athena-portfolio-query server for back-compat.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_NEW_GATE = _SCRIPT_DIR / "validate_mcp_surface.py"


def _load_new_gate():
    spec = importlib.util.spec_from_file_location(
        "validate_mcp_surface", _NEW_GATE
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("validate_mcp_surface", module)
    spec.loader.exec_module(module)
    return module


_new_gate = _load_new_gate()

# Re-export the API so existing callers (tests, importers) keep their
# references intact.
build_diff_report = _new_gate.build_diff_report
load_snapshot = _new_gate.load_snapshot
render_summary = _new_gate.render_summary
obtain_live_surface_for_server = _new_gate.obtain_live_surface_for_server
shutil = _new_gate.shutil  # type: ignore[attr-defined]
subprocess = _new_gate.subprocess  # type: ignore[attr-defined]


def obtain_live_surface(args, snapshot_path):
    """Back-compat wrapper for the original obtain_live_surface signature.

    The original function took an argparse Namespace with `live`,
    `athena_site_repo`, and `out` fields and worked on the athena-site repo.
    We map that to the registry entry for athena-portfolio-query.
    """
    server = {
        "id": "athena-portfolio-query",
        "name": "Athena Portfolio Query MCP Server",
        "repo": "athena-site",
        "server_path": "apps/mcp-server",
        "snapshot_path": "apps/mcp-server/tool-surface.snapshot.json",
        "snapshot_script": "npm run --silent snapshot",
        "runtime": "node",
        "enabled": True,
    }
    explicit_live = getattr(args, "live", None)
    if explicit_live is not None:
        return _new_gate.load_snapshot(Path(explicit_live).resolve()), (
            f"file:{Path(explicit_live).resolve()}"
        )
    return _new_gate.obtain_live_surface_for_server(
        server, snapshot_path, getattr(args, "athena_site_repo", None)
    )


def main(argv: list[str] | None = None) -> int:
    """Legacy CLI: defaults to gating only athena-portfolio-query.

    If neither --snapshot nor --live nor --server-id is given, we inject
    --server-id athena-portfolio-query so the gate stays single-server-shaped
    for callers that pre-date the registry.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    flags = set(argv)
    has_snapshot_live = any(
        a in flags or a.startswith("--snapshot=") or a.startswith("--live=")
        for a in argv + ["--snapshot", "--live"]
    )
    has_server_id = any(
        a == "--server-id" or a.startswith("--server-id=") for a in argv
    )
    has_all = "--all" in flags
    explicit_snapshot = "--snapshot" in argv
    explicit_live = "--live" in argv
    if (
        not explicit_snapshot
        and not explicit_live
        and not has_server_id
        and not has_all
    ):
        argv = ["--server-id", "athena-portfolio-query", *argv]
    # Suppress 'has_snapshot_live' warning (used for analysis only above).
    _ = has_snapshot_live
    return _new_gate.main(argv)


if __name__ == "__main__":
    sys.exit(main())

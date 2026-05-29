"""Tests for the registry-aware multi-server drift gate.

DEC-MCPSEC-008 parameterized the drift gate over `config/mcp_server_registry.yaml`.
These tests cover:

  - registry loading + validation (happy path, malformed YAML, missing fields,
    duplicate ids, wrong types)
  - the --all default that iterates every enabled server
  - --server-id selecting one entry from the registry
  - the `enabled: false` skip
  - multi-server gating with two registered servers (one matches, one drifts)
  - aggregate exit-code rules: 0 = all match, 1 = any drift, 2 = misconfigured
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "validate_mcp_surface.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_mcp_surface", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("validate_mcp_surface", module)
    spec.loader.exec_module(module)
    return module


gate = _load_module()


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


# ---------- helpers --------------------------------------------------------


def _write_snapshot(path: Path, tools: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": "0.1.0", "tools": tools}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _baseline_tools() -> list[dict]:
    return [
        {"name": "t1", "description": "d", "input_schema_hash": HASH_A},
        {"name": "t2", "description": "d", "input_schema_hash": HASH_A},
    ]


def _build_fake_server(
    tmp_path: Path,
    sid: str,
    tools: list[dict],
) -> tuple[Path, Path]:
    """Build a fake server directory layout and committed snapshot.

    Returns (repo_root, snapshot_file).
    """
    repo_root = tmp_path / sid / "repo"
    server_dir = repo_root / "apps" / "mcp-server"
    server_dir.mkdir(parents=True)
    snapshot_file = server_dir / "tool-surface.snapshot.json"
    _write_snapshot(snapshot_file, tools)
    return repo_root, snapshot_file


def _write_registry(path: Path, entries: list[dict]) -> Path:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"version": 1, "servers": entries}, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _server_entry(sid: str, repo_dirname: str, enabled: bool = True) -> dict:
    return {
        "id": sid,
        "name": f"Test Server {sid}",
        "repo": repo_dirname,
        "server_path": "apps/mcp-server",
        "snapshot_path": "apps/mcp-server/tool-surface.snapshot.json",
        "snapshot_script": "npm run snapshot",
        "runtime": "node",
        "enabled": enabled,
    }


# ---------- registry parsing ----------------------------------------------


def test_load_registry_happy_path(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yaml"
    _write_registry(
        registry_path,
        [_server_entry("server-a", "repo-a"), _server_entry("server-b", "repo-b")],
    )
    parsed = gate.load_registry(registry_path)
    assert len(parsed) == 2
    assert [s["id"] for s in parsed] == ["server-a", "server-b"]


def test_load_registry_missing_file(tmp_path: Path) -> None:
    with pytest.raises(gate.RegistryError, match="not found"):
        gate.load_registry(tmp_path / "does-not-exist.yaml")


def test_load_registry_malformed_yaml(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text("version: 1\nservers: [garbage:\n  - oops", encoding="utf-8")
    with pytest.raises(gate.RegistryError, match="YAML parse error"):
        gate.load_registry(registry_path)


def test_load_registry_wrong_version(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yaml"
    import yaml

    registry_path.write_text(
        yaml.safe_dump({"version": 99, "servers": [_server_entry("x", "y")]}),
        encoding="utf-8",
    )
    with pytest.raises(gate.RegistryError, match="unsupported registry version"):
        gate.load_registry(registry_path)


def test_load_registry_empty_servers(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yaml"
    import yaml

    registry_path.write_text(yaml.safe_dump({"version": 1, "servers": []}), encoding="utf-8")
    with pytest.raises(gate.RegistryError, match="non-empty array"):
        gate.load_registry(registry_path)


def test_load_registry_missing_required_field(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yaml"
    entry = _server_entry("a", "repo-a")
    del entry["snapshot_path"]
    _write_registry(registry_path, [entry])
    with pytest.raises(gate.RegistryError, match="snapshot_path"):
        gate.load_registry(registry_path)


def test_load_registry_duplicate_ids(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yaml"
    _write_registry(
        registry_path,
        [_server_entry("same", "repo-a"), _server_entry("same", "repo-b")],
    )
    with pytest.raises(gate.RegistryError, match="duplicate server id"):
        gate.load_registry(registry_path)


def test_load_registry_enabled_wrong_type(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.yaml"
    entry = _server_entry("a", "repo-a")
    entry["enabled"] = "yes"  # type: ignore[assignment]
    _write_registry(registry_path, [entry])
    with pytest.raises(gate.RegistryError, match="must be boolean"):
        gate.load_registry(registry_path)


# ---------- CLI behaviour --------------------------------------------------


def _setup_two_servers(
    tmp_path: Path,
    server_a_drift: bool = False,
    server_b_drift: bool = False,
    server_b_enabled: bool = True,
) -> tuple[Path, dict[str, Path]]:
    """Build a registry + two fake server layouts.

    Returns (registry_path, {sid: live_snapshot_path}). For each server we
    write a live snapshot that matches or diverges from the committed
    snapshot based on the drift flags.
    """
    a_committed = _baseline_tools()
    b_committed = _baseline_tools()

    repo_a, snap_a = _build_fake_server(tmp_path, "server-a", a_committed)
    repo_b, snap_b = _build_fake_server(tmp_path, "server-b", b_committed)

    # Build live surfaces in separate files; the gate reads them via
    # <ID_UPPER>_LIVE_SNAPSHOT env vars so we don't need to invoke npm.
    live_a_tools = list(a_committed)
    if server_a_drift:
        live_a_tools.append(
            {"name": "rogue_a", "description": "d", "input_schema_hash": HASH_C}
        )
    live_a = tmp_path / "live-a.json"
    _write_snapshot(live_a, live_a_tools)

    live_b_tools = list(b_committed)
    if server_b_drift:
        live_b_tools.append(
            {"name": "rogue_b", "description": "d", "input_schema_hash": HASH_B}
        )
    live_b = tmp_path / "live-b.json"
    _write_snapshot(live_b, live_b_tools)

    registry_path = tmp_path / "registry.yaml"
    # Use repo paths the gate can resolve via env vars (we set
    # <ID>_REPO below); the registry entry only declares the dirname so
    # the sibling-directory fallback would also work if env vars were
    # absent.
    _write_registry(
        registry_path,
        [
            _server_entry("server-a", repo_a.name),
            _server_entry("server-b", repo_b.name, enabled=server_b_enabled),
        ],
    )

    return registry_path, {
        "server-a": live_a,
        "server-b": live_b,
        "_repo_server-a": repo_a,
        "_repo_server-b": repo_b,
    }


def _apply_env(monkeypatch: pytest.MonkeyPatch, paths: dict[str, Path]) -> None:
    monkeypatch.setenv("SERVER_A_REPO", str(paths["_repo_server-a"]))
    monkeypatch.setenv("SERVER_B_REPO", str(paths["_repo_server-b"]))
    monkeypatch.setenv("SERVER_A_LIVE_SNAPSHOT", str(paths["server-a"]))
    monkeypatch.setenv("SERVER_B_LIVE_SNAPSHOT", str(paths["server-b"]))


def test_main_all_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry_path, paths = _setup_two_servers(tmp_path)
    _apply_env(monkeypatch, paths)
    reports_dir = tmp_path / "reports"

    exit_code = gate.main([
        "--all",
        "--registry", str(registry_path),
        "--reports-dir", str(reports_dir),
    ])
    assert exit_code == 0

    # Each enabled server gets a per-server diff report.
    report_a = json.loads((reports_dir / "mcp-surface-diff.server-a.json").read_text("utf-8"))
    report_b = json.loads((reports_dir / "mcp-surface-diff.server-b.json").read_text("utf-8"))
    assert report_a["drift_detected"] is False
    assert report_b["drift_detected"] is False
    assert report_a["server_id"] == "server-a"
    assert report_b["server_id"] == "server-b"


def test_main_no_flag_defaults_to_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No --all and no --server-id should behave like --all."""
    registry_path, paths = _setup_two_servers(tmp_path)
    _apply_env(monkeypatch, paths)
    reports_dir = tmp_path / "reports"

    exit_code = gate.main([
        "--registry", str(registry_path),
        "--reports-dir", str(reports_dir),
    ])
    assert exit_code == 0
    assert (reports_dir / "mcp-surface-diff.server-a.json").is_file()
    assert (reports_dir / "mcp-surface-diff.server-b.json").is_file()


def test_main_one_drifts_exits_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry_path, paths = _setup_two_servers(tmp_path, server_b_drift=True)
    _apply_env(monkeypatch, paths)
    reports_dir = tmp_path / "reports"

    exit_code = gate.main([
        "--all",
        "--registry", str(registry_path),
        "--reports-dir", str(reports_dir),
    ])
    assert exit_code == 1

    report_a = json.loads((reports_dir / "mcp-surface-diff.server-a.json").read_text("utf-8"))
    report_b = json.loads((reports_dir / "mcp-surface-diff.server-b.json").read_text("utf-8"))
    assert report_a["drift_detected"] is False
    assert report_b["drift_detected"] is True
    assert report_b["summary"]["added"] == 1
    assert report_b["added_tools"][0]["name"] == "rogue_b"


def test_main_disabled_server_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Server B is disabled AND would drift if gated. Exit code must be 0
    # because B is skipped entirely; A passes.
    registry_path, paths = _setup_two_servers(
        tmp_path, server_b_drift=True, server_b_enabled=False
    )
    _apply_env(monkeypatch, paths)
    reports_dir = tmp_path / "reports"

    exit_code = gate.main([
        "--all",
        "--registry", str(registry_path),
        "--reports-dir", str(reports_dir),
    ])
    assert exit_code == 0
    assert (reports_dir / "mcp-surface-diff.server-a.json").is_file()
    # The disabled server emits no report.
    assert not (reports_dir / "mcp-surface-diff.server-b.json").exists()


def test_main_server_id_targets_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry_path, paths = _setup_two_servers(tmp_path, server_b_drift=True)
    _apply_env(monkeypatch, paths)
    reports_dir = tmp_path / "reports"

    # Target only server-a, which doesn't drift. Should exit 0 even though
    # server-b would drift if it were included.
    exit_code = gate.main([
        "--server-id", "server-a",
        "--registry", str(registry_path),
        "--reports-dir", str(reports_dir),
    ])
    assert exit_code == 0
    assert (reports_dir / "mcp-surface-diff.server-a.json").is_file()
    assert not (reports_dir / "mcp-surface-diff.server-b.json").exists()


def test_main_unknown_server_id_returns_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path, paths = _setup_two_servers(tmp_path)
    _apply_env(monkeypatch, paths)

    exit_code = gate.main([
        "--server-id", "does-not-exist",
        "--registry", str(registry_path),
        "--reports-dir", str(tmp_path / "reports"),
    ])
    assert exit_code == 2


def test_main_missing_snapshot_returns_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path, paths = _setup_two_servers(tmp_path)
    _apply_env(monkeypatch, paths)

    # Delete server-a's snapshot file. The gate should report misconfigured
    # for server-a (exit 2) even if server-b would otherwise pass.
    snap_a = paths["_repo_server-a"] / "apps" / "mcp-server" / "tool-surface.snapshot.json"
    snap_a.unlink()

    exit_code = gate.main([
        "--all",
        "--registry", str(registry_path),
        "--reports-dir", str(tmp_path / "reports"),
    ])
    assert exit_code == 2


def test_committed_registry_loads(tmp_path: Path) -> None:
    """The repo's committed config/mcp_server_registry.yaml must parse."""
    committed = ROOT / "config" / "mcp_server_registry.yaml"
    parsed = gate.load_registry(committed)
    # At least one server registered, and the athena-portfolio-query
    # entry is enabled by default.
    assert parsed
    ids = [s["id"] for s in parsed]
    assert "athena-portfolio-query" in ids

"""Tests for the single-server (athena-portfolio-query) drift gate path.

DEC-MCPSEC-008 renamed the gate to scripts/validate_mcp_surface.py and
parameterized it over the MCP server registry. The athena-site-specific
script is now a thin back-compat alias. These tests exercise the
single-server CLI contract end-to-end against the new gate module.

Strategy: each test writes a small snapshot + a small live JSON to a tmp
directory and invokes main() with --snapshot and --live so the gate has no
external dependencies. The schema for the diff report is checked against
schemas/mcp-surface-diff.schema.json.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import jsonschema  # type: ignore[import-untyped]
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "validate_mcp_surface.py"
SCHEMA_PATH = ROOT / "schemas" / "mcp-surface-diff.schema.json"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "validate_mcp_surface", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("validate_mcp_surface", module)
    spec.loader.exec_module(module)
    return module


validator_module = _load_module()


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def _write_snapshot(path: Path, tools: list[dict]) -> Path:
    path.write_text(
        json.dumps({"version": "0.1.0", "tools": tools}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _seven_tool_baseline() -> list[dict]:
    return [
        {"name": "decisions_get", "description": "d", "input_schema_hash": HASH_A},
        {"name": "decisions_list", "description": "d", "input_schema_hash": HASH_A},
        {"name": "events_query", "description": "d", "input_schema_hash": HASH_A},
        {"name": "runs_get", "description": "d", "input_schema_hash": HASH_A},
        {"name": "runs_list", "description": "d", "input_schema_hash": HASH_A},
        {"name": "schemas_get", "description": "d", "input_schema_hash": HASH_A},
        {"name": "schemas_list", "description": "d", "input_schema_hash": HASH_A},
    ]


def test_matching_snapshots_pass(tmp_path: Path) -> None:
    baseline = _seven_tool_baseline()
    snapshot_path = _write_snapshot(tmp_path / "snap.json", baseline)
    live_path = _write_snapshot(tmp_path / "live.json", baseline)
    report_path = tmp_path / "report.json"

    exit_code = validator_module.main([
        "--snapshot", str(snapshot_path),
        "--live", str(live_path),
        "--out", str(report_path),
    ])

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["drift_detected"] is False
    assert report["summary"]["unchanged"] == 7
    assert report["summary"]["added"] == 0
    assert report["summary"]["removed"] == 0
    assert report["summary"]["changed"] == 0


def test_added_tool_is_drift(tmp_path: Path) -> None:
    snapshot_tools = _seven_tool_baseline()
    live_tools = snapshot_tools + [
        {"name": "rogue_tool", "description": "d", "input_schema_hash": HASH_B},
    ]
    snapshot_path = _write_snapshot(tmp_path / "snap.json", snapshot_tools)
    live_path = _write_snapshot(tmp_path / "live.json", live_tools)
    report_path = tmp_path / "report.json"

    exit_code = validator_module.main([
        "--snapshot", str(snapshot_path),
        "--live", str(live_path),
        "--out", str(report_path),
    ])

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["drift_detected"] is True
    assert report["summary"]["added"] == 1
    assert report["added_tools"][0]["name"] == "rogue_tool"


def test_removed_tool_is_drift(tmp_path: Path) -> None:
    snapshot_tools = _seven_tool_baseline()
    live_tools = [t for t in snapshot_tools if t["name"] != "events_query"]
    snapshot_path = _write_snapshot(tmp_path / "snap.json", snapshot_tools)
    live_path = _write_snapshot(tmp_path / "live.json", live_tools)
    report_path = tmp_path / "report.json"

    exit_code = validator_module.main([
        "--snapshot", str(snapshot_path),
        "--live", str(live_path),
        "--out", str(report_path),
    ])

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["drift_detected"] is True
    assert report["summary"]["removed"] == 1
    assert report["removed_tools"][0]["name"] == "events_query"


def test_changed_input_schema_hash_is_drift(tmp_path: Path) -> None:
    snapshot_tools = _seven_tool_baseline()
    live_tools = []
    for tool in snapshot_tools:
        copy = dict(tool)
        if copy["name"] == "runs_list":
            copy["input_schema_hash"] = HASH_C
        live_tools.append(copy)
    snapshot_path = _write_snapshot(tmp_path / "snap.json", snapshot_tools)
    live_path = _write_snapshot(tmp_path / "live.json", live_tools)
    report_path = tmp_path / "report.json"

    exit_code = validator_module.main([
        "--snapshot", str(snapshot_path),
        "--live", str(live_path),
        "--out", str(report_path),
    ])

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["drift_detected"] is True
    assert report["summary"]["changed"] == 1
    changed = report["changed_tools"][0]
    assert changed["name"] == "runs_list"
    assert changed["snapshot"]["input_schema_hash"] == HASH_A
    assert changed["live"]["input_schema_hash"] == HASH_C


def test_changed_description_is_drift(tmp_path: Path) -> None:
    snapshot_tools = _seven_tool_baseline()
    live_tools = []
    for tool in snapshot_tools:
        copy = dict(tool)
        if copy["name"] == "schemas_get":
            copy["description"] = "rephrased"
        live_tools.append(copy)
    snapshot_path = _write_snapshot(tmp_path / "snap.json", snapshot_tools)
    live_path = _write_snapshot(tmp_path / "live.json", live_tools)
    report_path = tmp_path / "report.json"

    exit_code = validator_module.main([
        "--snapshot", str(snapshot_path),
        "--live", str(live_path),
        "--out", str(report_path),
    ])

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["changed"] == 1


def test_missing_snapshot_returns_two(tmp_path: Path) -> None:
    live_path = _write_snapshot(tmp_path / "live.json", _seven_tool_baseline())
    report_path = tmp_path / "report.json"

    exit_code = validator_module.main([
        "--snapshot", str(tmp_path / "does-not-exist.json"),
        "--live", str(live_path),
        "--out", str(report_path),
    ])

    assert exit_code == 2


def test_malformed_snapshot_returns_two(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snap.json"
    snapshot_path.write_text("{ not json", encoding="utf-8")
    live_path = _write_snapshot(tmp_path / "live.json", _seven_tool_baseline())
    report_path = tmp_path / "report.json"

    exit_code = validator_module.main([
        "--snapshot", str(snapshot_path),
        "--live", str(live_path),
        "--out", str(report_path),
    ])

    assert exit_code == 2


def test_report_conforms_to_diff_schema(tmp_path: Path) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    snapshot_tools = _seven_tool_baseline()
    live_tools = snapshot_tools + [
        {"name": "added_tool", "description": "d", "input_schema_hash": HASH_B},
    ]
    snapshot_path = _write_snapshot(tmp_path / "snap.json", snapshot_tools)
    live_path = _write_snapshot(tmp_path / "live.json", live_tools)
    report_path = tmp_path / "report.json"

    exit_code = validator_module.main([
        "--snapshot", str(snapshot_path),
        "--live", str(live_path),
        "--out", str(report_path),
    ])

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=report, schema=schema)


def test_obtain_live_surface_preserves_snapshot_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The snapshot-script-regeneration path must restore the committed
    snapshot byte-for-byte, including line endings. Regression test for the
    Windows CRLF<->LF text-mode corruption that left the LF-committed
    snapshot dirty after every gate run.
    """
    import subprocess

    # Build a fake athena-site layout under tmp_path.
    mcp_dir = tmp_path / "apps" / "mcp-server"
    mcp_dir.mkdir(parents=True)
    snapshot_file = mcp_dir / "tool-surface.snapshot.json"

    # LF-only payload, the exact line-ending shape the real committed
    # snapshot uses. If text-mode I/O is anywhere on the backup/restore
    # path, this body will come back as CRLF on Windows.
    original_bytes = (
        b'{\n  "version": "0.1.0",\n  "tools": [\n'
        b'    {"name": "t1", "description": "d", "input_schema_hash": "'
        + (b"a" * 64)
        + b'"}\n  ]\n}\n'
    )
    snapshot_file.write_bytes(original_bytes)
    pre_bytes = snapshot_file.read_bytes()
    assert b"\r\n" not in pre_bytes  # sanity

    # The "live" surface the fake snapshot script would produce. Mismatched
    # content guarantees the restore is what put the original back, not
    # a no-op.
    live_payload = {
        "version": "0.1.0",
        "tools": [
            {"name": "t1", "description": "d", "input_schema_hash": "b" * 64},
            {"name": "t2", "description": "d", "input_schema_hash": "c" * 64},
        ],
    }

    def fake_which(name: str) -> str:
        assert name == "npm"
        return "/fake/npm"

    def fake_run(cmd, cwd, capture_output, text, check):  # noqa: ANN001
        # Simulate the snapshot script by overwriting the file with the
        # live payload (this is what the snapshot script writes in reality).
        snapshot_file.write_text(
            json.dumps(live_payload, indent=2) + "\n", encoding="utf-8"
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(validator_module.shutil, "which", fake_which)
    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)

    server = {
        "id": "athena-portfolio-query",
        "name": "Athena Portfolio Query MCP Server",
        "repo": "athena-site",
        "server_path": "apps/mcp-server",
        "snapshot_path": "apps/mcp-server/tool-surface.snapshot.json",
        "snapshot_script": "npm run snapshot",
        "runtime": "node",
        "enabled": True,
    }
    live, label = validator_module.obtain_live_surface_for_server(
        server, snapshot_file, tmp_path
    )

    # Live surface came from the simulated snapshot script.
    assert {t["name"] for t in live["tools"]} == {"t1", "t2"}
    assert label.startswith("script:npm run snapshot@")

    # Snapshot file restored byte-for-byte. No CRLF leakage.
    post_bytes = snapshot_file.read_bytes()
    assert post_bytes == original_bytes
    assert b"\r\n" not in post_bytes


def test_against_real_athena_site_snapshot(tmp_path: Path) -> None:
    real_snapshot = (
        ROOT / ".." / "athena-site" / "apps" / "mcp-server" / "tool-surface.snapshot.json"
    ).resolve()
    if not real_snapshot.is_file():
        pytest.skip("athena-site sibling repo not present; skip live-snapshot check")
    report_path = tmp_path / "report.json"
    exit_code = validator_module.main([
        "--snapshot", str(real_snapshot),
        "--live", str(real_snapshot),
        "--out", str(report_path),
    ])
    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["drift_detected"] is False
    assert report["summary"]["unchanged"] == 7

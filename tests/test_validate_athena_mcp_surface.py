"""Tests for scripts/validate_athena_mcp_surface.py.

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
SCRIPT_PATH = ROOT / "scripts" / "validate_athena_mcp_surface.py"
SCHEMA_PATH = ROOT / "schemas" / "mcp-surface-diff.schema.json"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "validate_athena_mcp_surface", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("validate_athena_mcp_surface", module)
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

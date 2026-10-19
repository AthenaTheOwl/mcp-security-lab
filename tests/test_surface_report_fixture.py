"""Keep clean-checkout conformance tied to the real report producer."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load_producer():
    spec = importlib.util.spec_from_file_location(
        "surface_fixture_producer", ROOT / "scripts/validate_mcp_surface.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tool(name: str, digest: str) -> dict:
    return {"name": name, "description": "Synthetic fixture tool.",
            "input_schema_hash": digest * 64}


def test_synthetic_report_matches_producer_and_schema() -> None:
    module = _load_producer()
    report = module.build_diff_report(
        snapshot={"tools": [tool("unchanged", "a"), tool("changed", "a"),
                            tool("removed", "b")]},
        live={"tools": [tool("unchanged", "a"), tool("changed", "b"),
                        tool("added", "c")]},
        snapshot_path=Path("synthetic-snapshot.json"),
        live_source="synthetic fixture; no server contacted",
        server_id="synthetic-fixture",
    )
    # The fixed timestamp marks fixture data, not an observation of a live server.
    report["generated_at"] = "2026-10-18T00:00:00Z"
    fixture = json.loads((ROOT / "examples/mcp-surface-diff.synthetic.json").read_text())
    assert report == fixture
    schema = json.loads((ROOT / "schemas/mcp-surface-diff.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(fixture)


def test_conformance_globs_cover_every_report_the_gate_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The README says the conformance gate checks the reports the surface
    gate writes under reports/. Run both gate modes into a scratch reports/
    directory and check the conformance globs pick up every file."""
    module = _load_producer()
    reports = tmp_path / "reports"
    monkeypatch.setattr(module, "DEFAULT_REPORTS_DIR", reports)
    surface = tmp_path / "surface.json"
    surface.write_text(json.dumps({"tools": [tool("one", "a")]}), encoding="utf-8")

    # Ad-hoc mode writes reports/mcp-surface-diff.json.
    assert module.main(["--snapshot", str(surface), "--live", str(surface)]) == 0

    # Registry mode writes reports/mcp-surface-diff.<server-id>.json.
    repo = tmp_path / "repo"
    (repo / "srv").mkdir(parents=True)
    (repo / "srv/snapshot.json").write_text(surface.read_text(), encoding="utf-8")
    registry = tmp_path / "registry.yaml"
    registry.write_text(yaml.safe_dump({"version": 1, "servers": [{
        "id": "fixture-server", "name": "Fixture server", "repo": "repo",
        "server_path": "srv", "snapshot_path": "srv/snapshot.json",
        "snapshot_script": "npm run snapshot", "runtime": "node",
    }]}), encoding="utf-8")
    monkeypatch.setenv("FIXTURE_SERVER_REPO", str(repo))
    monkeypatch.setenv("FIXTURE_SERVER_LIVE_SNAPSHOT", str(surface))
    assert module.main(["--all", "--registry", str(registry)]) == 0

    written = {p.relative_to(tmp_path).as_posix() for p in reports.iterdir()}
    assert written == {"reports/mcp-surface-diff.json",
                       "reports/mcp-surface-diff.fixture-server.json"}
    config = yaml.safe_load((ROOT / "schemas/conformance.yaml").read_text())
    (mapping,) = [m for m in config["mappings"]
                  if m["schema"] == "mcp-surface-diff.schema.json"]
    matched = {p.relative_to(tmp_path).as_posix()
               for pattern in mapping["files"] for p in tmp_path.glob(pattern)}
    assert written <= matched

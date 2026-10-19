"""Keep clean-checkout conformance tied to the real report producer."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_report_matches_producer_and_schema() -> None:
    spec = importlib.util.spec_from_file_location(
        "surface_fixture_producer", ROOT / "scripts/validate_mcp_surface.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def tool(name: str, digest: str) -> dict:
        return {"name": name, "description": "Synthetic fixture tool.",
                "input_schema_hash": digest * 64}

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

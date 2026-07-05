"""Pin the real-config scorecard so scanner changes that move precision/recall fail CI.

The corpus (``eval/corpus/``) and ground truth (``eval/labels.json``) are frozen,
publicly-sourced inputs. This test recomputes the scorecard from them with the
current scanner and asserts it matches the committed
``reports/eval-scorecard.json`` (and the rendered Markdown) byte-for-byte. If a
future scanner edit shifts a detection outcome, the recomputed numbers diverge
from the committed ones and this test fails, forcing an intentional scorecard
update.
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp_security_lab.eval import (
    CATEGORIES,
    build_scorecard,
    load_eval_inputs,
    render_scorecard_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
CORPUS_DIR = EVAL_DIR / "corpus"
JSON_REPORT = ROOT / "reports" / "eval-scorecard.json"
MD_REPORT = ROOT / "reports" / "eval-scorecard.md"


def _committed_scorecard() -> dict:
    return json.loads(JSON_REPORT.read_text(encoding="utf-8"))


def test_scorecard_matches_committed_json() -> None:
    assert build_scorecard(EVAL_DIR) == _committed_scorecard(), (
        "Recomputed scorecard differs from reports/eval-scorecard.json. If this is an "
        "intended scanner change, run `python scripts/generate_eval_scorecard.py` and "
        "review the precision/recall delta before committing."
    )


def test_scorecard_markdown_matches_committed() -> None:
    _, labels, _ = load_eval_inputs(EVAL_DIR)
    rendered = render_scorecard_markdown(build_scorecard(EVAL_DIR), labels)
    assert rendered == MD_REPORT.read_text(encoding="utf-8"), (
        "Rendered scorecard Markdown differs from reports/eval-scorecard.md; "
        "regenerate with scripts/generate_eval_scorecard.py."
    )


def test_scorecard_is_deterministic() -> None:
    assert build_scorecard(EVAL_DIR) == build_scorecard(EVAL_DIR)


def test_headline_numbers_are_legible() -> None:
    # These mirror the committed scorecard; they document intent and make a
    # regression's meaning obvious in the test output, not just the diff.
    card = _committed_scorecard()
    overall = card["overall"]
    assert overall["fp"] == 0, "scanner should raise no false alarms on the real corpus"
    assert overall["precision"] == 1.0
    assert overall["recall"] == 1.0
    assert overall["tp"] == 26 and overall["fn"] == 0

    per = card["per_category"]
    assert per["COMMAND_EXECUTION"]["precision"] == 1.0
    assert per["COMMAND_EXECUTION"]["recall"] == 1.0
    assert per["UNAUTH_REMOTE"]["recall"] == 1.0
    assert per["BROAD_FILESYSTEM"]["recall"] == 1.0
    # PROMPT_INJECTION has no positive support in real config files.
    assert per["PROMPT_INJECTION"]["support_positive"] == 0
    assert per["PROMPT_INJECTION"]["precision"] is None


def test_every_labeled_config_has_a_fixture_and_vice_versa() -> None:
    _, labels, manifest = load_eval_inputs(EVAL_DIR)
    labeled = set(labels["labels"])
    fixtures = {p.stem for p in CORPUS_DIR.glob("*.json")}
    manifest_ids = {e["id"] for e in manifest["entries"]}
    assert labeled == fixtures == manifest_ids, (
        "corpus / labels / manifest must cover exactly the same config ids"
    )
    assert manifest["config_count"] == len(fixtures)


def test_labels_cover_every_category_for_every_server() -> None:
    _, labels, _ = load_eval_inputs(EVAL_DIR)
    for config_id, servers in labels["labels"].items():
        for server_name, cats in servers.items():
            missing = set(CATEGORIES) - set(cats)
            assert not missing, f"{config_id}/{server_name} missing labels: {missing}"

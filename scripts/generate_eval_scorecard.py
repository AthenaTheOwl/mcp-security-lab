"""Regenerate the real-config scanner scorecard.

Runs the existing scanner over the committed corpus under ``eval/`` and writes a
deterministic scorecard to ``reports/eval-scorecard.json`` and
``reports/eval-scorecard.md``. No network, no timestamps: the output is a pure
function of the committed corpus + labels + scanner, so
``tests/test_eval_scorecard.py`` can assert the committed numbers never drift
unnoticed.

    python scripts/generate_eval_scorecard.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp_security_lab.eval import (  # noqa: E402
    build_scorecard,
    load_eval_inputs,
    render_scorecard_markdown,
)

EVAL_DIR = ROOT / "eval"
JSON_OUT = ROOT / "reports" / "eval-scorecard.json"
MD_OUT = ROOT / "reports" / "eval-scorecard.md"


def main() -> int:
    scorecard = build_scorecard(EVAL_DIR)
    _, labels, _ = load_eval_inputs(EVAL_DIR)
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    MD_OUT.write_text(render_scorecard_markdown(scorecard, labels), encoding="utf-8")
    o = scorecard["overall"]
    print(f"Wrote {JSON_OUT} and {MD_OUT}")
    print(
        f"overall: precision={o['precision']} recall={o['recall']} "
        f"tp={o['tp']} fp={o['fp']} fn={o['fn']} tn={o['tn']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

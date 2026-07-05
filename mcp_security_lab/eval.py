"""Score the static scanner against the real-config evaluation corpus.

The corpus under ``eval/`` holds verbatim, publicly documented MCP server
configurations (see ``eval/manifest.json``) with hand-labelled ground truth
(``eval/labels.json``). This module runs the existing scanner over that corpus
and computes per-category and overall precision / recall / FP / FN, entirely
deterministically: it calls :func:`score_server` directly, so no timestamps or
absolute paths enter the numbers.

Categories map one-to-one onto the scanner's decision rules:

===================  ================
category             scanner rule_id
===================  ================
COMMAND_EXECUTION    STDIO-COMMAND
BROAD_FILESYSTEM     BROAD-ACCESS
UNAUTH_REMOTE        REMOTE-NO-AUTH
PROMPT_INJECTION     INJECTION-CORPUS
===================  ================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_servers
from .scoring import score_server

CATEGORY_TO_RULE = {
    "COMMAND_EXECUTION": "STDIO-COMMAND",
    "BROAD_FILESYSTEM": "BROAD-ACCESS",
    "UNAUTH_REMOTE": "REMOTE-NO-AUTH",
    "PROMPT_INJECTION": "INJECTION-CORPUS",
}
CATEGORIES = list(CATEGORY_TO_RULE)

SCORECARD_VERSION = "1.0"

# One-line diagnoses for the specific false negatives / false positives the
# corpus surfaces. Keyed by (config_id, category). A generic fallback covers
# any cell not listed here, so the harness stays honest if labels change.
_DIAGNOSES: dict[tuple[str, str], str] = {
    ("05-git-docker-home-mount", "BROAD_FILESYSTEM"): (
        "MISS: docker bind-mount `src=/Users/username` exposes the whole $HOME, but "
        "BROAD-ACCESS only matches bare wildcard/root strings, never mount specs or "
        "path prefixes."
    ),
    ("22-mcp-remote-sse-noauth", "UNAUTH_REMOTE"): (
        "MISS: the remote SSE URL sits in `args` behind the `mcp-remote` proxy; "
        "REMOTE-NO-AUTH only inspects `url`/`endpoint`/`transport` fields, so a remote "
        "endpoint reached via a stdio proxy is scored as a plain local command."
    ),
}


def _fn_reason(config_id: str, category: str) -> str:
    return _DIAGNOSES.get(
        (config_id, category),
        f"MISS: ground truth {category} is present but rule "
        f"{CATEGORY_TO_RULE[category]} did not fire.",
    )


def _fp_reason(config_id: str, category: str) -> str:
    return _DIAGNOSES.get(
        (config_id, category),
        f"FALSE ALARM: rule {CATEGORY_TO_RULE[category]} fired but ground truth "
        f"{category} is negative.",
    )


def load_eval_inputs(eval_dir: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """Return ``(corpus_dir, labels, manifest)`` for the eval directory."""
    manifest = json.loads((eval_dir / "manifest.json").read_text(encoding="utf-8"))
    labels = json.loads((eval_dir / "labels.json").read_text(encoding="utf-8"))
    return eval_dir / "corpus", labels, manifest


def _metrics(tp: int, fp: int, fn: int) -> dict[str, Any]:
    precision = round(tp / (tp + fp), 4) if (tp + fp) else None
    recall = round(tp / (tp + fn), 4) if (tp + fn) else None
    if precision and recall:
        f1: float | None = round(2 * precision * recall / (precision + recall), 4)
    else:
        f1 = None
    return {"precision": precision, "recall": recall, "f1": f1}


def build_scorecard(eval_dir: Path) -> dict[str, Any]:
    """Run the scanner over the committed corpus and return the scorecard dict.

    Deterministic: iterates configs in sorted id order and scores servers with
    :func:`score_server`. The returned dict carries no timestamps or paths, so a
    test can compare it byte-for-byte against the committed scorecard.
    """
    corpus_dir, labels, manifest = load_eval_inputs(eval_dir)
    label_map = labels["labels"]

    per_cat = {c: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for c in CATEGORIES}
    support = {c: 0 for c in CATEGORIES}
    fp_findings: list[dict[str, str]] = []
    fn_findings: list[dict[str, str]] = []

    for config_id in sorted(label_map):
        servers = {s.name: s for s in load_servers(corpus_dir / f"{config_id}.json")}
        for server_name in sorted(label_map[config_id]):
            cat_labels = label_map[config_id][server_name]
            server = servers[server_name]
            fired = {f["rule_id"] for f in score_server(server)["findings"]}
            for cat in CATEGORIES:
                actual = bool(cat_labels[cat])
                predicted = CATEGORY_TO_RULE[cat] in fired
                support[cat] += int(actual)
                cell = per_cat[cat]
                if predicted and actual:
                    cell["tp"] += 1
                elif predicted and not actual:
                    cell["fp"] += 1
                    fp_findings.append({
                        "config": config_id, "server": server_name,
                        "category": cat, "rule": CATEGORY_TO_RULE[cat],
                        "diagnosis": _fp_reason(config_id, cat),
                    })
                elif not predicted and actual:
                    cell["fn"] += 1
                    fn_findings.append({
                        "config": config_id, "server": server_name,
                        "category": cat, "rule": CATEGORY_TO_RULE[cat],
                        "diagnosis": _fn_reason(config_id, cat),
                    })
                else:
                    cell["tn"] += 1

    per_category = {}
    tot = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for cat in CATEGORIES:
        cell = per_cat[cat]
        for k in tot:
            tot[k] += cell[k]
        per_category[cat] = {
            **cell,
            "support_positive": support[cat],
            **_metrics(cell["tp"], cell["fp"], cell["fn"]),
        }

    overall = {**tot, **_metrics(tot["tp"], tot["fp"], tot["fn"])}

    return {
        "scorecard_version": SCORECARD_VERSION,
        "corpus": {
            "name": manifest.get("corpus_name"),
            "config_count": manifest.get("config_count"),
            "server_count": manifest.get("server_count"),
            "curated_at": manifest.get("curated_at"),
            "source_breakdown": manifest.get("source_breakdown", {}),
        },
        "categories": CATEGORIES,
        "category_rule_map": CATEGORY_TO_RULE,
        "per_category": per_category,
        "overall": overall,
        "false_positives": fp_findings,
        "false_negatives": fn_findings,
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def render_scorecard_markdown(scorecard: dict[str, Any], labels: dict[str, Any]) -> str:
    corpus = scorecard["corpus"]
    lines = [
        "# Real-Config Scanner Scorecard",
        "",
        "Precision / recall of the static MCP config scanner measured against "
        f"**{corpus['config_count']} real, publicly documented** MCP server "
        f"configurations ({corpus['server_count']} servers) — not self-authored "
        "synthetic fixtures. Corpus and provenance: `eval/manifest.json`; ground "
        "truth: `eval/labels.json`. Regenerate with "
        "`python scripts/generate_eval_scorecard.py`.",
        "",
        "This scorecard is deterministic: it is recomputed from the committed corpus "
        "and asserted in `tests/test_eval_scorecard.py`, so any scanner change that "
        "shifts precision/recall fails CI.",
        "",
        "## Corpus",
        "",
        f"- Configs: {corpus['config_count']} | Servers: {corpus['server_count']} | "
        f"Curated: {corpus['curated_at']}",
        "- Public sources only; secret values kept as upstream placeholders.",
        "",
        "| Source repo | Configs |",
        "| --- | ---: |",
    ]
    for repo, count in sorted(corpus["source_breakdown"].items()):
        lines.append(f"| `{repo}` | {count} |")

    lines += [
        "",
        "## Precision / recall",
        "",
        "Each category maps to one scanner rule. A cell is one (config x server x "
        "category) decision. `support+` = ground-truth-positive cells.",
        "",
        "| Category | Rule | TP | FP | FN | TN | support+ | Precision | Recall | F1 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cat in scorecard["categories"]:
        m = scorecard["per_category"][cat]
        lines.append(
            f"| {cat} | `{scorecard['category_rule_map'][cat]}` | {m['tp']} | {m['fp']} | "
            f"{m['fn']} | {m['tn']} | {m['support_positive']} | {_pct(m['precision'])} | "
            f"{_pct(m['recall'])} | {_pct(m['f1'])} |"
        )
    o = scorecard["overall"]
    lines.append(
        f"| **Overall (micro)** | — | {o['tp']} | {o['fp']} | {o['fn']} | {o['tn']} | "
        f"{o['tp'] + o['fn']} | {_pct(o['precision'])} | {_pct(o['recall'])} | "
        f"{_pct(o['f1'])} |"
    )

    lines += ["", "## False positives", ""]
    if scorecard["false_positives"]:
        for fp in scorecard["false_positives"]:
            lines.append(f"- `{fp['config']}` / {fp['server']} [{fp['category']}]: {fp['diagnosis']}")
    else:
        lines.append("None. The scanner raised zero false alarms across the four "
                     "decision categories on this corpus.")

    lines += ["", "## False negatives", ""]
    if scorecard["false_negatives"]:
        for fn in scorecard["false_negatives"]:
            lines.append(f"- `{fn['config']}` / {fn['server']} [{fn['category']}]: {fn['diagnosis']}")
    else:
        lines.append("None.")

    defs = labels.get("category_definitions", {})
    lines += ["", "## Ground-truth definitions", ""]
    for cat in scorecard["categories"]:
        if cat in defs:
            lines.append(f"- **{cat}**: {defs[cat]}")

    ambiguous = labels.get("ambiguous_cases", {})
    if ambiguous:
        lines += ["", "## Ambiguous labels", ""]
        for cid, note in sorted(ambiguous.items()):
            lines.append(f"- `{cid}`: {note}")

    lines += [
        "",
        "## Scope note",
        "",
        "`PROMPT_INJECTION` has zero positive support: real `claude_desktop_config.json` "
        "files carry only `command`/`args`/`env`, never tool descriptions or prompts, so "
        "the injection corpus (the scanner's most sophisticated feature) has no attack "
        "surface in the artifact it scans. Injection risk lives in runtime tool metadata, "
        "which is out of static-config scope. Precision/recall are therefore undefined "
        "(n/a) for that category here, with zero false alarms.",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"

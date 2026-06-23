"""mcp-security-lab — live demo (Streamlit Community Cloud).

Reads the committed report under reports/example.json directly (no network,
no secrets) and renders the same config risk review the `show` verb prints:
which MCP server in a config you should not allowlist, and why.

Deploy: Streamlit Community Cloud -> New app -> repo AthenaTheOwl/mcp-security-lab,
branch main, main file streamlit_app.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

REPO = Path(__file__).resolve().parent
REPORT_PATH = REPO / "reports" / "example.json"


def load_report() -> dict | None:
    if not REPORT_PATH.exists():
        return None
    try:
        return json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


st.set_page_config(page_title="mcp-security-lab — config risk review", layout="wide")
st.title("mcp-security-lab")
st.caption(
    "a 30-second preflight check for MCP server configs: which server in a config "
    "you should not allowlist, and why. reads the committed example report directly."
)

report = load_report()
if not report:
    st.warning("no report found at reports/example.json")
    st.stop()

summary = report["summary"]
counts = summary["risk_counts"]
servers = sorted(report["servers"], key=lambda s: s["risk_score"], reverse=True)

c1, c2, c3 = st.columns(3)
c1.metric("servers scanned", summary["server_count"])
c2.metric("max risk score", summary["max_score"], help="0-100, higher is riskier")
c3.metric(
    "high + critical",
    counts["high"] + counts["critical"],
    help=f"low={counts['low']} medium={counts['medium']} high={counts['high']} critical={counts['critical']}",
)

st.caption(f"source config: `{report['source']}`")

levels = ["critical", "high", "medium", "low"]
selected = st.multiselect(
    "filter by risk level",
    options=levels,
    default=levels,
    help="hide lower-risk servers to focus the review",
)
shown = [s for s in servers if s["risk_level"] in selected]


def _verdict(server: dict) -> str:
    policy = server.get("policy")
    return policy["verdict"] if isinstance(policy, dict) else "-"


st.dataframe(
    [
        {
            "rank": i,
            "server": s["name"],
            "score": s["risk_score"],
            "level": s["risk_level"],
            "transport": s["transport"],
            "read-only": s["read_only"],
            "policy verdict": _verdict(s),
            "findings": len(s.get("findings", [])),
            "injection matches": len(s.get("injection_matches", [])),
        }
        for i, s in enumerate(shown, start=1)
    ],
    use_container_width=True,
    hide_index=True,
)

if servers:
    top = servers[0]
    inj = top.get("injection_matches", [])
    phrases = sorted({m["match"].lower() for m in inj})
    denied = [s["name"] for s in servers if _verdict(s) == "deny"]
    callout = (
        f"**highest-risk server: {top['name']}** — score {top['risk_score']}/100 "
        f"({top['risk_level']}), policy verdict `{_verdict(top)}`."
    )
    if phrases:
        callout += f" injection phrases ({len(inj)}): {', '.join(phrases)}."
    if denied:
        callout += f" do not allowlist: {', '.join(denied)}."
    (st.error if top["risk_level"] == "critical" else st.info)(callout)

    with st.expander(f"evidence for {top['name']}"):
        flagged = [
            f for f in top.get("findings", [])
            if f["severity"] in ("high", "critical") or f.get("score_delta", 0) > 0
        ]
        if flagged:
            st.markdown("**flagged findings**")
            for f in flagged:
                st.markdown(
                    f"- `{f['rule_id']}` ({f['severity']}, {f['score_delta']:+}): "
                    f"{f['message']}  \n  evidence: `{f['evidence']}`"
                )
        if inj:
            st.markdown("**injection matches**")
            for m in inj:
                st.markdown(
                    f"- `{m['rule_id']}` in `{m['field']}`: \"{m['match']}\"  \n"
                    f"  evidence: `{m['evidence']}`"
                )

st.caption(
    "the scanner + scoring live in `mcp_security_lab/`; this page reads the committed "
    "`reports/example.json`, mirroring `python -m mcp_security_lab show`. "
    "repo: github.com/AthenaTheOwl/mcp-security-lab"
)

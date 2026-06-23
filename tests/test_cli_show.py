from __future__ import annotations

from mcp_security_lab.cli import main


def test_show_no_args_prints_ranked_summary(capsys) -> None:
    exit_code = main(["show"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "servers ranked by risk score" in out
    assert "local-filesystem-shell" in out
    assert "policy verdicts:" in out

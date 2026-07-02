from __future__ import annotations

import pytest

from mcp_security_lab.cli import main


def test_show_no_args_prints_ranked_summary(capsys) -> None:
    exit_code = main(["show"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "servers ranked by risk score" in out
    assert "local-filesystem-shell" in out
    assert "policy verdicts:" in out


def test_scan_missing_config_exits_cleanly(capsys) -> None:
    # A typo'd input path should exit non-zero with an actionable message on
    # stderr, not a raw traceback.
    with pytest.raises(SystemExit) as excinfo:
        main(["scan", "does-not-exist.json", "--out", "out.json"])

    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "does-not-exist.json" in err
    assert "cannot read" in err


def test_diff_missing_baseline_exits_cleanly(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "diff",
                "--baseline",
                "missing-baseline.json",
                "--current",
                "missing-current.json",
                "--out",
                "diff.json",
            ]
        )

    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "missing-baseline.json" in err
    assert "cannot read" in err

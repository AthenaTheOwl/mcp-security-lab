from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "validate_sensitive_disclosures.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_sensitive_disclosures", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("validate_sensitive_disclosures", module)
    spec.loader.exec_module(module)
    return module


gate = _load_module()


def test_blocks_literal_google_key_without_printing_secret(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    doc = repo / "README.md"
    secret = "AIza" + "A" * 35
    doc.write_text(f"key = {secret}\n", encoding="utf-8")

    assert gate.main([str(repo), "--root", str(repo)]) == 1
    captured = capsys.readouterr()
    assert "google-api-key" in captured.err
    assert secret not in captured.err


def test_blocks_filter_repo_command_in_markdown(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    doc = repo / "runbook.md"
    doc.write_text("Run git filter-repo --replace-text replacements.txt\n", encoding="utf-8")

    assert gate.main([str(repo), "--root", str(repo)]) == 1
    assert "filter-repo-literal-risk" in capsys.readouterr().err


def test_blocks_key_tail_or_fingerprint_disclosure(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    doc = repo / "audit.md"
    doc.write_text("fingerprint abcdef1234567890, key ending wxyz\n", encoding="utf-8")

    assert gate.main([str(repo), "--root", str(repo)]) == 1
    err = capsys.readouterr().err
    assert "secret-fingerprint-disclosure" in err
    assert "abcdef1234567890" not in err


def test_allows_sanitized_incident_note(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    doc = repo / "notice.md"
    doc.write_text(
        "Credential issue handled offline. Current source uses placeholders only.\n",
        encoding="utf-8",
    )

    assert gate.main([str(repo), "--root", str(repo)]) == 0


def test_own_gate_files_are_allowlisted() -> None:
    findings = gate.scan([SCRIPT_PATH], root=ROOT)
    assert findings == []

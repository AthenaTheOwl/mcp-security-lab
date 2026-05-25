from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "specs" / "0001-mcp-security-lab"
REQUIREMENTS = SPEC_DIR / "requirements.md"
TRACEABILITY = SPEC_DIR / "traceability.md"
DECISION_DIR = ROOT / "decisions"


REQ_PATTERN = re.compile(r"\bR-MCPSEC-\d{3}\b")
DEC_PATTERN = re.compile(r"\bDEC-MCPSEC-\d{3}[-\w]*\b")


def main() -> int:
    errors: list[str] = []
    requirements_text = REQUIREMENTS.read_text(encoding="utf-8")
    trace_text = TRACEABILITY.read_text(encoding="utf-8")

    requirements = sorted(set(REQ_PATTERN.findall(requirements_text)))
    traced = set(REQ_PATTERN.findall(trace_text))
    for requirement in requirements:
        if requirement not in traced:
            errors.append(f"{requirement} missing from traceability.md")

    for line_number, line in enumerate(requirements_text.splitlines(), 1):
        if REQ_PATTERN.search(line) and "owner_role:" not in line:
            errors.append(f"requirements.md:{line_number}: requirement lacks owner_role token")

    for line_number, line in enumerate(trace_text.splitlines(), 1):
        requirement = REQ_PATTERN.search(line)
        if requirement and "DEC-MCPSEC-" not in line and "allowlist:" not in line:
            errors.append(f"traceability.md:{line_number}: {requirement.group(0)} lacks DEC coverage or allowlist")

    for decision_id in sorted(set(DEC_PATTERN.findall(trace_text))):
        if not list(DECISION_DIR.glob(f"{decision_id}*.md")):
            errors.append(f"{decision_id} referenced in traceability.md but no decision file exists")

    if errors:
        print("\n".join(errors))
        return 1
    print("spec_check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())


from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_GLOBS = ["README.md", "specs/**/*.md", "decisions/**/*.md"]
BANNED = [
    "leverage",
    "comprehensive",
    "robust",
    "seamless",
    "powerful",
    "elegant",
    "thoughtful",
    "innovative",
    "transformative",
    "revolutionary",
    "the point is",
    "in conclusion",
    "ultimately",
    "importantly",
    "notably",
    "moreover",
    "furthermore",
]


def main() -> int:
    failures: list[str] = []
    for path in _doc_paths():
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), 1):
            for term in BANNED:
                pattern = re.compile(rf"(?<![\w-]){re.escape(term)}(?![\w-])", re.IGNORECASE)
                if pattern.search(line):
                    failures.append(f"{path.relative_to(ROOT)}:{line_number}: banned voice term: {term}")
    if failures:
        print("\n".join(failures))
        return 1
    print("voice_lint: clean")
    return 0


def _doc_paths() -> list[Path]:
    paths: set[Path] = set()
    for pattern in DOC_GLOBS:
        paths.update(ROOT.glob(pattern))
    return sorted(path for path in paths if path.is_file())


if __name__ == "__main__":
    sys.exit(main())


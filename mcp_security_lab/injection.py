from __future__ import annotations

import re
from typing import Any


INJECTION_PATTERNS = {
    "ignore_previous": re.compile(r"\bignore\s+(all\s+)?previous\b", re.IGNORECASE),
    "exfiltrate": re.compile(r"\bexfiltrat(?:e|ion|ing)\b", re.IGNORECASE),
    "reveal_secrets": re.compile(r"\breveal\s+(?:the\s+)?secrets?\b", re.IGNORECASE),
    "disable_safety": re.compile(r"\bdisable\s+(?:all\s+)?safet(?:y|ies)\b", re.IGNORECASE),
    "run_shell": re.compile(r"\brun\s+(?:a\s+)?shell\b|\bshell\s+command\b", re.IGNORECASE),
    "write_file": re.compile(r"\bwrite\s+(?:a\s+)?file\b", re.IGNORECASE),
    "install_package": re.compile(r"\binstall\s+(?:an?\s+)?package\b", re.IGNORECASE),
}


def scan_injection_texts(server_name: str, raw: dict[str, Any]) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for field, text in iter_descriptor_texts(raw):
        normalized = text.replace("_", " ")
        for pattern_id, pattern in INJECTION_PATTERNS.items():
            hit = pattern.search(normalized)
            if hit:
                matches.append(
                    {
                        "server": server_name,
                        "rule_id": f"INJECT-{pattern_id.upper()}",
                        "field": field,
                        "match": hit.group(0),
                        "evidence": _shorten(text),
                    }
                )
    return matches


def iter_descriptor_texts(raw: dict[str, Any]) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    for key in ("name", "description", "prompt", "instructions"):
        value = raw.get(key)
        if isinstance(value, str):
            texts.append((key, value))
    for collection_name in ("tools", "toolDescriptors", "prompts"):
        collection = raw.get(collection_name)
        if isinstance(collection, list):
            for index, item in enumerate(collection):
                texts.extend(_texts_from_descriptor(collection_name, index, item))
        elif isinstance(collection, dict):
            for name, item in collection.items():
                if isinstance(name, str):
                    texts.append((f"{collection_name}.{name}.name", name))
                texts.extend(_texts_from_descriptor(collection_name, name, item))
    return texts


def _texts_from_descriptor(collection_name: str, index: object, item: Any) -> list[tuple[str, str]]:
    if isinstance(item, str):
        return [(f"{collection_name}.{index}", item)]
    if not isinstance(item, dict):
        return []
    texts: list[tuple[str, str]] = []
    for key in ("name", "title", "description", "prompt", "instructions"):
        value = item.get(key)
        if isinstance(value, str):
            texts.append((f"{collection_name}.{index}.{key}", value))
    return texts


def _shorten(text: str, limit: int = 160) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


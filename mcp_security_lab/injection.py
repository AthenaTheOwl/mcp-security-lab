from __future__ import annotations

import re
from typing import Any


INJECTION_PATTERNS = {
    # Override / suppression
    "ignore_previous": re.compile(r"\bignore\s+(all\s+)?previous\b", re.IGNORECASE),
    "ignore_instructions": re.compile(
        r"\bignore\s+(?:the\s+)?(?:above|prior|previous|earlier)\s+instructions?\b",
        re.IGNORECASE,
    ),
    "disable_safety": re.compile(r"\bdisable\s+(?:all\s+)?safet(?:y|ies)\b", re.IGNORECASE),
    "forget_system_prompt": re.compile(
        r"\bforget\s+(?:the\s+|your\s+)?(?:system\s+)?prompt\b", re.IGNORECASE
    ),
    # Exfiltration
    "exfiltrate": re.compile(r"\bexfiltrat(?:e|ion|ing)\b", re.IGNORECASE),
    "send_to_external": re.compile(
        r"\bsend\s+[^.\n]{1,40}?\s+to\s+(?:an?\s+)?external\b", re.IGNORECASE
    ),
    "upload_to_url": re.compile(
        r"\bupload\s+(?:to|via)\s+(?:a\s+)?(?:url|webhook|endpoint)\b", re.IGNORECASE
    ),
    "reveal_secrets": re.compile(r"\breveal\s+(?:the\s+)?secrets?\b", re.IGNORECASE),
    # Role override / impersonation
    "you_are_now": re.compile(r"\byou\s+are\s+now\s+(?:a|an|the)\b", re.IGNORECASE),
    "act_as_system": re.compile(
        r"\bact\s+as\s+(?:a\s+|the\s+)?(?:system|root|admin|developer)\b", re.IGNORECASE
    ),
    "system_note_prefix": re.compile(
        r"^\s*(?:\[?system\s*(?:note|message)\]?|<\s*system\s*>)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "assistant_impersonation": re.compile(
        r"\b(?:assistant|model):\s*(?:i\s+will|sure|certainly)\b", re.IGNORECASE
    ),
    # Output redirection / persistence
    "write_file": re.compile(r"\bwrite\s+(?:a\s+)?file\b", re.IGNORECASE),
    "save_as": re.compile(
        r"\bsave\s+(?:as|to)\s+(?:a\s+|the\s+)?(?:file|disk)\b", re.IGNORECASE
    ),
    # Execution / install
    "run_shell": re.compile(r"\brun\s+(?:a\s+)?shell\b|\bshell\s+command\b", re.IGNORECASE),
    "install_package": re.compile(r"\binstall\s+(?:an?\s+)?package\b", re.IGNORECASE),
    "curl_pipe_sh": re.compile(
        r"\bcurl\s+[^\n]+\|\s*(?:bash|sh|zsh)\b", re.IGNORECASE
    ),
    # Indirect / obfuscation
    "base64_encoded_instruction": re.compile(
        r"\b(?:base64|b64)(?:-?(?:encode|decode))?\b.{0,80}\b(?:instruction|prompt|payload)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "unicode_confusable_ignore": re.compile(
        # Common confusable-character substitutions of injection verbs.
        # The Latin lowercase 'i' is often replaced with Cyrillic 'і'
        # (U+0456) or Latin small letter dotless i (U+0131) to slip past
        # ASCII-only filters: "іgnore", "ɪgnore". The Cyrillic 'е' (U+0435)
        # likewise replaces Latin 'e' in "rеveal".
        r"[ɪіⅰιⅼ]gnore\b|r[еeē]veal",
        re.IGNORECASE | re.UNICODE,
    ),
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


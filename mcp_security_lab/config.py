from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ServerConfig:
    name: str
    raw: dict[str, Any]


def load_servers(path: Path) -> list[ServerConfig]:
    data = _load_json(path)
    return normalize_servers(data)


def normalize_servers(data: Any) -> list[ServerConfig]:
    if isinstance(data, dict):
        if "mcpServers" in data:
            return _from_collection(data["mcpServers"])
        if "servers" in data:
            return _from_collection(data["servers"])
        if _looks_like_server(data):
            return [_coerce_server(data, fallback_name="server-1")]
    if isinstance(data, list):
        return _from_collection(data)
    raise ValueError("expected mcpServers, servers, a server object, or a flat server list")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def _from_collection(value: Any) -> list[ServerConfig]:
    if isinstance(value, dict):
        return [_coerce_server(server, fallback_name=name) for name, server in value.items()]
    if isinstance(value, list):
        return [_coerce_server(server, fallback_name=f"server-{index}") for index, server in enumerate(value, 1)]
    raise ValueError("server collection must be a mapping or list")


def _coerce_server(value: Any, fallback_name: str) -> ServerConfig:
    if not isinstance(value, dict):
        raise ValueError(f"server {fallback_name} must be an object")
    raw = dict(value)
    name = str(raw.get("name") or raw.get("id") or fallback_name)
    return ServerConfig(name=name, raw=raw)


def _looks_like_server(value: dict[str, Any]) -> bool:
    server_keys = {
        "name",
        "id",
        "command",
        "args",
        "env",
        "transport",
        "url",
        "endpoint",
        "tools",
        "toolDescriptors",
        "prompts",
        "resources",
    }
    return bool(server_keys.intersection(value))


from __future__ import annotations

from mcp_security_lab.config import normalize_servers


def test_loads_mcp_servers_mapping() -> None:
    servers = normalize_servers({"mcpServers": {"alpha": {"command": "node"}}})

    assert len(servers) == 1
    assert servers[0].name == "alpha"
    assert servers[0].raw["command"] == "node"


def test_loads_servers_list() -> None:
    servers = normalize_servers({"servers": [{"name": "beta", "transport": "sse"}]})

    assert [server.name for server in servers] == ["beta"]


def test_loads_flat_list() -> None:
    servers = normalize_servers([{"id": "gamma", "url": "https://example.com/mcp"}])

    assert servers[0].name == "gamma"


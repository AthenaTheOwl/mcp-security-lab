from __future__ import annotations

from typing import Any

from .config import ServerConfig
from .injection import scan_injection_texts


KEYWORD_GROUPS = {
    "filesystem": ("file", "files", "filesystem", "directory", "folder", "path", "read_file", "write_file"),
    "shell": ("shell", "bash", "powershell", "cmd", "terminal", "exec"),
    "process": ("process", "spawn", "subprocess", "kill", "pid"),
    "git": ("git", "commit", "push", "pull", "clone"),
    "network": ("http", "https", "network", "fetch", "curl", "wget", "socket"),
    "browser": ("browser", "web", "page", "click", "screenshot"),
    "email": ("email", "gmail", "imap", "smtp", "send_mail"),
    "db": ("db", "database", "sql", "postgres", "mysql", "sqlite", "redis"),
    "secrets": ("secret", "token", "credential", "password", "api_key", "apikey", "ssh"),
    "env": ("env", "environment", "dotenv"),
}

BROAD_PATHS = {"/", "\\", "~", "$HOME", "%USERPROFILE%", "C:\\", "C:/", "D:\\", "D:/"}
AUTH_KEYS = {"auth", "authorization", "headers", "token", "oauth", "bearerToken", "apiKey", "api_key"}


def score_server(server: ServerConfig) -> dict[str, Any]:
    raw = server.raw
    findings: list[dict[str, Any]] = []
    score = 0

    if _has_stdio_command(raw):
        score = max(score, 60)
        findings.append(_finding("STDIO-COMMAND", "high", "server starts a local command", "command", 60))

    descriptor_text = " ".join(_string_values(raw)).lower().replace("_", " ")
    matched_groups = _matched_keyword_groups(descriptor_text)

    if "filesystem" in matched_groups:
        score += 20
        findings.append(_finding("FILESYSTEM-SURFACE", "medium", "filesystem-like tool or config text", "descriptor", 20))

    sensitive_groups = sorted(matched_groups - {"filesystem"})
    if sensitive_groups:
        delta = min(40, 8 * len(sensitive_groups))
        score += delta
        findings.append(
            _finding(
                "SENSITIVE-KEYWORDS",
                "medium",
                f"sensitive keyword groups: {', '.join(sensitive_groups)}",
                "descriptor",
                delta,
            )
        )

    if _remote_url_without_auth(raw):
        score += 35
        findings.append(_finding("REMOTE-NO-AUTH", "high", "remote URL transport lacks auth metadata", "url", 35))

    broad_hits = _broad_access_hits(raw)
    if broad_hits:
        score += 20
        findings.append(
            _finding(
                "BROAD-ACCESS",
                "medium",
                "wildcard env or broad path root detected",
                ", ".join(sorted(set(broad_hits))),
                20,
            )
        )

    injection_matches = scan_injection_texts(server.name, raw)
    if injection_matches:
        score += 25
        findings.append(
            _finding(
                "INJECTION-CORPUS",
                "high",
                f"{len(injection_matches)} prompt or tool-injection phrase(s) matched",
                "descriptors",
                25,
            )
        )

    read_only = _is_read_only_resource_server(raw)
    if read_only and not _has_stdio_command(raw) and not _remote_url_without_auth(raw):
        score = max(5, score - 20)
        findings.append(_finding("READONLY-RESOURCE", "info", "read-only resource server lowers risk", "resources", -20))

    score = max(0, min(100, score))
    return {
        "name": server.name,
        "risk_score": score,
        "risk_level": _risk_level(score),
        "transport": _transport(raw),
        "read_only": read_only,
        "findings": findings,
        "injection_matches": injection_matches,
    }


def _has_stdio_command(raw: dict[str, Any]) -> bool:
    transport = str(raw.get("transport", "")).lower()
    return "command" in raw or transport == "stdio"


def _remote_url_without_auth(raw: dict[str, Any]) -> bool:
    transport = str(raw.get("transport", "")).lower()
    server_type = str(raw.get("type", "")).lower()
    has_remote = any(
        isinstance(raw.get(key), str) and raw[key].startswith(("http://", "https://"))
        for key in ("url", "endpoint")
    )
    has_remote = has_remote or transport in {"http", "https", "sse", "streamable_http", "remote"}
    has_remote = has_remote or server_type in {"http", "https", "sse", "streamable_http", "remote"}
    has_remote = has_remote or _has_remote_proxy_url(raw)
    if not has_remote:
        return False
    return not _has_auth_metadata(raw)


def _has_auth_metadata(raw: dict[str, Any]) -> bool:
    for key in raw:
        if key in AUTH_KEYS:
            return True
        if key.lower() in {auth_key.lower() for auth_key in AUTH_KEYS}:
            return True
    env = raw.get("env")
    if isinstance(env, dict):
        return any(any(auth in str(key).lower() for auth in ("token", "key", "auth")) for key in env)
    return False


def _matched_keyword_groups(text: str) -> set[str]:
    groups: set[str] = set()
    for group, keywords in KEYWORD_GROUPS.items():
        if any(keyword.replace("_", " ") in text for keyword in keywords):
            groups.add(group)
    return groups


def _broad_access_hits(raw: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    env = raw.get("env")
    if isinstance(env, dict):
        for key, value in env.items():
            value_text = str(value)
            if value_text.strip() in {"*", ".*"} or value_text.endswith("*"):
                hits.append(f"env.{key}={value_text}")
    for value in _string_values(raw):
        stripped = value.strip()
        if stripped in BROAD_PATHS:
            hits.append(stripped)
        if stripped.lower() in {"c:\\users", "c:/users", "/users", "/home"}:
            hits.append(stripped)
        mount_hit = _broad_mount_source(stripped)
        if mount_hit is not None:
            hits.append(mount_hit)
    return hits


def _has_remote_proxy_url(raw: dict[str, Any]) -> bool:
    """Detect remote endpoints hidden behind stdio proxy commands.

    Real-world configs often run ``npx mcp-remote https://...``. That is still
    a remote MCP endpoint even though the top-level transport is local stdio.
    Keep this intentionally narrow: a random URL in a description should not
    become a transport finding.
    """
    args = raw.get("args")
    if not isinstance(args, list):
        return False
    arg_texts = [str(arg) for arg in args]
    command = str(raw.get("command", ""))
    has_proxy = "mcp-remote" in command or any("mcp-remote" in arg for arg in arg_texts)
    if not has_proxy:
        return False
    return any(arg.startswith(("http://", "https://")) for arg in arg_texts)


def _broad_mount_source(value: str) -> str | None:
    """Return the broad source path from a docker-style mount argument.

    Supports ``--mount type=bind,src=/Users/name,dst=/container`` and the
    shorter volume form ``/Users/name:/container``. Only root/home-style
    sources count; project-scoped paths stay quiet to preserve precision.
    """
    source: str | None = None
    if "type=bind" in value and ("," in value or "=" in value):
        for part in value.split(","):
            key, sep, raw_part_value = part.partition("=")
            if sep and key.strip().lower() in {"src", "source"}:
                source = raw_part_value.strip()
                break
    elif ":" in value and not value.startswith(("http://", "https://")):
        source = value.split(":", 1)[0].strip()

    if not source:
        return None
    normalized = source.replace("\\", "/").rstrip("/")
    lowered = normalized.lower()
    if source in BROAD_PATHS or normalized in {"/", "~", "$HOME", "%USERPROFILE%"}:
        return f"mount.src={source}"
    if lowered in {"c:/users", "/users", "/home"}:
        return f"mount.src={source}"
    if _is_user_home_path(lowered):
        return f"mount.src={source}"
    return None


def _is_user_home_path(path: str) -> bool:
    normalized = path.strip("/")
    parts = [part for part in normalized.split("/") if part]
    if len(parts) == 2 and parts[0] in {"users", "home"}:
        return True
    if len(parts) == 3 and len(parts[0]) == 2 and parts[0][1] == ":" and parts[1] == "users":
        return True
    return False


def _is_read_only_resource_server(raw: dict[str, Any]) -> bool:
    text = " ".join(_string_values(raw)).lower().replace("_", "-")
    if "read-only" in text or "readonly" in text:
        return True
    resources = raw.get("resources")
    tools = raw.get("tools")
    if resources and not tools:
        return True
    if isinstance(tools, list) and tools:
        tool_names = []
        for tool in tools:
            if isinstance(tool, dict):
                tool_names.append(str(tool.get("name", "")))
            elif isinstance(tool, str):
                tool_names.append(tool)
        if tool_names and all(name.lower().startswith(("read", "list", "get", "fetch")) for name in tool_names):
            return True
    return False


def _transport(raw: dict[str, Any]) -> str:
    if "transport" in raw:
        return str(raw["transport"])
    if "command" in raw:
        return "stdio"
    if "url" in raw or "endpoint" in raw:
        return "remote"
    return "unknown"


def _risk_level(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _finding(rule_id: str, severity: str, message: str, evidence: str, score_delta: int) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "evidence": evidence,
        "score_delta": score_delta,
    }


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values: list[str] = []
        for key, item in value.items():
            values.append(str(key))
            values.extend(_string_values(item))
        return values
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(_string_values(item))
        return values
    return []


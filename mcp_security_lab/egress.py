from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path

import yaml

DATA_FILE = Path(__file__).resolve().parent / "data" / "egress_hosts.yaml"
WEBFETCH = re.compile(r"^WebFetch\(\s*domain:([^)\s]+)\s*\)$")
LIST_KEYS = ("shorteners", "form_or_paste", "tunnels", "public_suffixes")

RULES = {
    "egress.wildcard": "wildcard over a registrable suffix lets any host under it receive data",
    "egress.shortener": "URL shortener hides the real destination and can redirect anywhere",
    "egress.form_or_paste": "form, paste or request-capture host turns an allowed request into a write",
    "egress.tunnel": "reverse tunnel forwards traffic to a machine the policy author does not control",
    "egress.raw_ip": "IP literal bypasses name-based review and reputation",
}

CAVEAT = (
    "A clean result means none of the listed patterns matched. A static read cannot see "
    "DNS exfiltration, runtime redirects, or hosts missing from data/egress_hosts.yaml."
)


def load_host_lists(path: Path = DATA_FILE) -> dict[str, list[str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {key: [str(v).lower() for v in data.get(key, [])] for key in LIST_KEYS}


def load_policy_hosts(path: Path) -> list[str]:
    """Return allowed hosts from a generic policy or a settings file's permissions.allow."""
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: not valid JSON or YAML ({exc.__class__.__name__})") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object with allowed_hosts or permissions.allow")
    hosts: list[str] = []
    found = False
    if "allowed_hosts" in data:
        found = True
        entries = data["allowed_hosts"]
        if not isinstance(entries, list) or not all(isinstance(e, str) for e in entries):
            raise ValueError(f"{path}: allowed_hosts must be a list of strings")
        hosts.extend(entries)
    permissions = data.get("permissions")
    if isinstance(permissions, dict) and "allow" in permissions:
        allow = permissions["allow"]
        if not isinstance(allow, list) or not all(isinstance(e, str) for e in allow):
            raise ValueError(f"{path}: permissions.allow must be a list of strings")
        found = True
        for entry in allow:
            match = WEBFETCH.match(entry.strip())
            if match:
                hosts.append(match.group(1))
    if not found:
        raise ValueError(f"{path}: no allowed_hosts list or permissions.allow list found")
    return hosts


def normalize_host(entry: str) -> str:
    host = entry.strip().lower()
    host = re.sub(r"^[a-z][a-z0-9+.-]*://", "", host)
    host = host.split("/", 1)[0]
    if host.startswith("["):
        return host[1:].split("]", 1)[0]
    if host.count(":") == 1:
        host = host.split(":", 1)[0]
    return host.rstrip(".")


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _under(host: str, domains: list[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def _is_broad_wildcard(host: str, public_suffixes: list[str]) -> bool:
    if "*" not in host:
        return False
    if not host.startswith("*."):
        return True  # bare * or a mid-label wildcard such as *com
    rest = host[2:]
    if "*" in rest:
        return True
    return "." not in rest or rest in public_suffixes


def check_hosts(entries: list[str], lists: dict[str, list[str]] | None = None) -> list[dict[str, str]]:
    lists = lists or load_host_lists()
    findings: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        host = normalize_host(entry)
        bare = host[2:] if host.startswith("*.") else host
        hits = []
        if _is_broad_wildcard(host, lists["public_suffixes"]):
            hits.append("egress.wildcard")
        if _is_ip(host):
            hits.append("egress.raw_ip")
        if _under(bare, lists["shorteners"]):
            hits.append("egress.shortener")
        if _under(bare, lists["form_or_paste"]):
            hits.append("egress.form_or_paste")
        if _under(bare, lists["tunnels"]):
            hits.append("egress.tunnel")
        for rule in hits:
            if (rule, host) not in seen:
                seen.add((rule, host))
                findings.append({"rule": rule, "host": host, "why": RULES[rule]})
    return findings


def run_egress(policy: Path, as_json: bool = False) -> int:
    entries = load_policy_hosts(policy)
    findings = check_hosts(entries)
    if as_json:
        print(json.dumps({"policy": str(policy), "hosts_checked": len(entries),
                          "findings": findings, "caveat": CAVEAT}, indent=2))
    else:
        for f in findings:
            print(f"{f['rule']}  {f['host']}  {f['why']}")
        print(f"{len(findings)} finding(s) across {len(entries)} allowed host(s).")
        print(CAVEAT)
    return 1 if findings else 0

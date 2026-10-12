from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_security_lab.cli import main
from mcp_security_lab.egress import check_hosts, load_policy_hosts

ROOT = Path(__file__).resolve().parent.parent
LEAKY = ROOT / "examples" / "egress" / "leaky-policy.json"
TIGHT = ROOT / "examples" / "egress" / "tight-policy.json"


def rules(hosts):
    return sorted({f["rule"] for f in check_hosts(hosts)})


def test_leaky_policy_exits_1_with_one_finding_per_rule(capsys):
    assert main(["egress", str(LEAKY), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert sorted(f["rule"] for f in payload["findings"]) == [
        "egress.form_or_paste",
        "egress.raw_ip",
        "egress.shortener",
        "egress.tunnel",
        "egress.wildcard",
    ]
    assert "DNS" in payload["caveat"]


def test_tight_policy_exits_0(capsys):
    assert main(["egress", str(TIGHT)]) == 0
    assert "0 finding(s)" in capsys.readouterr().out


@pytest.mark.parametrize("host", ["*", "*.com", "*.co.uk", "*.*", "*com"])
def test_wildcards_over_registrable_suffix(host):
    assert rules([host]) == ["egress.wildcard"]


def test_narrow_wildcard_is_allowed():
    assert check_hosts(["*.python.org"]) == []


@pytest.mark.parametrize("host", ["https://bit.ly/x", "go.t.co", "TinyURL.com"])
def test_shorteners_including_subdomain_scheme_and_case(host):
    assert rules([host]) == ["egress.shortener"]


def test_lookalike_host_does_not_match():
    assert check_hosts(["notbit.ly", "mybit.ly.example.com"]) == []


def test_form_paste_and_tunnel_hosts():
    assert rules(["pastebin.com", "abc.requestbin.com"]) == ["egress.form_or_paste"]
    assert rules(["x.trycloudflare.com", "*.ngrok.io"]) == ["egress.tunnel"]


def test_ip_literals_v4_v6_and_port():
    hosts = ["10.0.0.5:8080", "[::1]", "2001:db8::1"]
    assert rules(hosts) == ["egress.raw_ip"]
    assert len(check_hosts(hosts)) == 3


def test_webfetch_entries_from_settings_file(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"permissions": {"allow": [
        "WebFetch(domain:bit.ly)", "Bash(ls:*)", "WebFetch(domain:docs.python.org)"]}}))
    assert load_policy_hosts(p) == ["bit.ly", "docs.python.org"]
    assert main(["egress", str(p)]) == 1


def test_yaml_policy_accepted(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text("allowed_hosts:\n  - pypi.org\n")
    assert main(["egress", str(p)]) == 0


@pytest.mark.parametrize("body", ["[]", '{"hosts": ["a.com"]}', '{"allowed_hosts": "a.com"}',
                                  '{"allowed_hosts": [1]}', "{not json: ["])
def test_unknown_shapes_exit_2(tmp_path, body):
    p = tmp_path / "bad.json"
    p.write_text(body)
    with pytest.raises(SystemExit) as exc:
        main(["egress", str(p)])
    assert exc.value.code == 2


def test_missing_file_exit_2(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["egress", str(tmp_path / "nope.json")])
    assert exc.value.code == 2

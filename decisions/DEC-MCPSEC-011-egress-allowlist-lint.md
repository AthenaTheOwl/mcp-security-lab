---
id: DEC-MCPSEC-011-egress-allowlist-lint
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-EGRESS-001
date: 2026-10-12
status: approved
reversible: true
decision: |
  Add an `egress` verb that reads a network allowlist (a generic JSON or
  YAML `allowed_hosts` list, or `WebFetch(domain:...)` entries from a
  settings file's `permissions.allow`) and applies five deterministic
  rules: wildcard over a registrable suffix, URL shortener, form or paste
  host, reverse tunnel, and IP literal. Host lists live in one data file,
  `mcp_security_lab/data/egress_hosts.yaml`. Any other policy shape exits 2
  instead of passing silently. A clean run states that it only proves no
  listed pattern matched.
alternatives:
  - label: resolve hosts and follow redirects at lint time
    rejected_because: |
      That adds network access to a scanner that DEC-MCPSEC-001 keeps
      static, and makes results depend on what a host serves today.
  - label: parse every vendor's sandbox policy format
    rejected_because: |
      Formats differ and change. One generic shape plus the WebFetch
      form fails closed on the rest, and new readers can be added per
      format once a real file needs one.
rationale: |
  The scanner's config read already says network egress is not visible in
  config. An allowlist is where egress is declared, and the entries that
  let an allowed request carry data out are a short, stable set. Keeping
  the lists in data makes staleness a one-file fix.
evidence:
  - kind: spec
    ref: specs/0001-mcp-security-lab/requirements.md
  - kind: decision
    ref: decisions/DEC-MCPSEC-001-config-scan-before-runtime.md
rollback: |
  Remove the egress subcommand, mcp_security_lab/egress.py, the data
  file, the examples/egress fixtures and tests/test_egress.py. Scan,
  policy and diff gates do not depend on them.
owner: platform
systems_map: |
  An egress allowlist decides which writes leave the sandbox. Shorteners,
  form and paste hosts, and tunnels turn an allowed read into a write to
  an unreviewed destination; wildcards and IP literals remove the review.
transferable_principle: |
  Lint the declaration of a boundary for the entries that void it, and
  report what the lint cannot see alongside what it found.
falsification_test: |
  If a policy that lets a request reach an attacker-controlled host through
  one of the five listed patterns exits 0, the rule or its host list is
  wrong. If a tight policy exits 1, a rule is over-matching.
adoption_ladder:
  minimum_viable: |
    `egress POLICY` on a generic allowlist or settings file, five rules,
    exit 0 or 1, exit 2 on unknown shapes.
  mid_adoption: |
    Run in CI against the committed sandbox policy; extend
    egress_hosts.yaml as new shorteners and capture hosts appear.
  full_adoption: |
    Pair with a runtime DNS reachability probe from inside the sandbox for
    the cases a static read cannot see.
  monitoring_signals:
    - hosts found in incident review that no rule matched
    - false positives reported against the host lists
---

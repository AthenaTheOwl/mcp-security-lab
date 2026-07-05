---
id: DEC-MCPSEC-010-real-config-eval-scorecard
spec: specs/0001-mcp-security-lab/
requirement: R-MCPSEC-EVAL-001
date: 2026-07-05
status: approved
reversible: true
decision: |
  The scanner is scored against a committed corpus of real, publicly
  documented MCP configs (eval/) with a provenance manifest and
  hand-labelled ground truth, producing a deterministic precision/recall
  scorecard (reports/eval-scorecard.{json,md}) that a test pins so scanner
  changes shifting the numbers fail CI.
alternatives:
  - label: keep grading only against self-authored synthetic fixtures
    rejected_because: |
      Synthetic fixtures are written to fire the rules; they measure that
      the code runs, not that the rules match how real configs express
      risk. A 100/100 on a config an author built to score 100 says
      nothing about false-positive or false-negative rate on inputs the
      author did not anticipate. The synthetic golden-master tests
      (tests/test_scoring.py) stay — they lock the weights — but they are
      not evidence of real-world accuracy.
  - label: an LLM-judge over real configs instead of hand labels
    rejected_because: |
      DEC-MCPSEC-002 already chose a fixed policy corpus over an LLM
      judge for the scanner itself; grading the scanner with a
      nondeterministic judge would reintroduce exactly the drift and
      unauditability that decision rejected. Hand labels are frozen,
      reviewable, and let the scorecard be recomputed byte-for-byte.
  - label: fetch real configs live at test time
    rejected_because: |
      Network at test time is nondeterministic and offline-hostile, and
      upstream READMEs change. Verbatim snapshots under eval/corpus/ with
      source_url + fetched_at in the manifest keep the corpus reproducible
      and the provenance auditable without a network call.
rationale: |
  The lab's claim is "flagship-grade static risk scanner." That claim is
  only testable against inputs the author did not construct. This DEC adds
  25 verbatim configs drawn from modelcontextprotocol/servers,
  servers-archived, geelen/mcp-remote, and github/github-mcp-server, each
  with a source URL, fetch date, and license note, plus conservative
  per-category ground-truth labels.

  The scorecard is a pure function of corpus + labels + scanner: no
  timestamps, no paths, no network. That is what lets
  tests/test_eval_scorecard.py assert the committed numbers exactly, so a
  future rule edit that trades recall for noise (or vice versa) shows up
  as a failing test with a visible precision/recall delta, not as a silent
  regression. The scorecard also records every FP/FN with a one-line
  diagnosis, turning "the scanner missed X" into a tracked follow-up
  rather than folklore.

  Measured result on this corpus: overall precision 1.00, recall 0.92
  (24 TP, 0 FP, 2 FN over 100 category-cells). Command-execution detection
  is exact (P/R 1.0). The two misses are recall gaps where real configs
  express risk in forms the narrow patterns do not parse: a docker
  bind-mount of the whole home dir (BROAD-ACCESS) and a remote SSE URL
  behind the mcp-remote stdio proxy (REMOTE-NO-AUTH). Prompt-injection has
  zero attack surface in real config files, which carry no tool text.
evidence:
  - kind: code
    ref: mcp_security_lab/eval.py
  - kind: code
    ref: scripts/generate_eval_scorecard.py
  - kind: doc
    ref: eval/manifest.json
  - kind: doc
    ref: eval/labels.json
  - kind: run
    ref: reports/eval-scorecard.json
  - kind: run
    ref: reports/eval-scorecard.md
  - kind: test
    ref: tests/test_eval_scorecard.py
  - kind: decision
    ref: decisions/DEC-MCPSEC-002-policy-corpus-over-llm-judge.md
rollback: |
  Revert this DEC's commits: drop mcp_security_lab/eval.py,
  scripts/generate_eval_scorecard.py, the eval/ directory,
  reports/eval-scorecard.{json,md}, tests/test_eval_scorecard.py, the
  R-MCPSEC-EVAL-001 rows in requirements.md and traceability.md, and the
  two negation lines added to .gitignore. Nothing else depends on the
  eval module; the scanner and its synthetic tests are untouched.
owner: platform
systems_map: |
  Evaluation-against-real-inputs as a standing gate, not a one-off audit.
  The synthetic golden-master tests measure "does the code still compute
  the same weights"; the real-config scorecard measures "do the weights
  still match reality." Committing the corpus, labels, and numbers turns
  accuracy into a versioned artifact the same way the diff gate turned
  drift into one — a change to the scanner now has to reckon with its
  measured precision/recall, in the same commit.
transferable_principle: |
  A detector graded only on fixtures its authors wrote is unfalsified.
  Freeze a small, provenance-tracked corpus of real inputs with hand
  labels and pin the score; the corpus need not be large to expose the
  gap between "fires on my examples" and "matches the world."
falsification_test: |
  If a scanner change that visibly worsens real-world accuracy (e.g.
  widening a keyword list until it false-alarms on benign configs) can
  land with the full suite green, the scorecard is not actually gating
  accuracy and this DEC has failed. The committed FP/FN counts in
  reports/eval-scorecard.json are the tripwire.
adoption_ladder:
  minimum_viable: |
    25-config corpus with manifest + labels; deterministic scorecard
    committed and pinned by one regeneration test.
  mid_adoption: |
    Corpus grows to cover browser, remote-native-url, and multi-server
    configs; secondary keyword-heuristic categories (FILESYSTEM-SURFACE,
    SENSITIVE-KEYWORDS) get crisp labels and enter the scorecard.
  full_adoption: |
    Every scanner rule has real-config positive and negative support;
    the scorecard runs in CI and a precision/recall regression blocks
    merge; FP/FN diagnoses feed a scanner-accuracy backlog.
  monitoring_signals:
    - overall precision/recall per scorecard revision
    - count of FP/FN entries carried as open scanner follow-ups
    - corpus size and per-category positive support over time
---

## decision

The scanner is scored against a committed corpus of real, publicly
documented MCP server configurations under `eval/`, with a provenance
manifest (`eval/manifest.json`), hand-labelled ground truth
(`eval/labels.json`), and a deterministic precision/recall scorecard at
`reports/eval-scorecard.json` and `reports/eval-scorecard.md`.
`tests/test_eval_scorecard.py` regenerates the scorecard from the
committed corpus and asserts it matches, so any scanner change that shifts
precision or recall fails CI.

## alternatives

- Keep grading only against self-authored synthetic fixtures. Rejected:
  fixtures written to fire the rules measure that the code runs, not that
  the rules match real inputs. The synthetic golden-master tests stay (they
  lock the weights) but are not real-world accuracy evidence.
- Grade with an LLM judge over real configs. Rejected: DEC-MCPSEC-002
  already chose a fixed corpus over an LLM judge; a nondeterministic judge
  would reintroduce the drift that decision rejected.
- Fetch real configs live at test time. Rejected: network at test time is
  nondeterministic and offline-hostile. Verbatim snapshots with
  `source_url` + `fetched_at` keep the corpus reproducible and auditable.

## rationale

The lab claims flagship-grade static scanning. That claim is only testable
against inputs the author did not construct. This DEC adds 25 verbatim
configs from `modelcontextprotocol/servers`,
`modelcontextprotocol/servers-archived`, `geelen/mcp-remote`, and
`github/github-mcp-server`, each with source URL, fetch date, and license
note, plus conservative per-category ground-truth labels.

The scorecard is a pure function of corpus + labels + scanner, so the test
can pin the exact numbers. A rule edit that trades recall for noise now
surfaces as a failing test with a visible delta, not a silent regression.
Every FP/FN is recorded with a one-line diagnosis so misses become tracked
follow-ups.

Measured on this corpus: overall precision 1.00, recall 0.92 (24 TP, 0 FP,
2 FN over 100 category-cells). Command-execution detection is exact. The
two misses are recall gaps where real configs express risk in forms the
narrow patterns do not parse (whole-home docker mount; remote SSE behind
the mcp-remote proxy). Prompt-injection has no attack surface in real
config files, which carry no tool text.

## evidence

- `mcp_security_lab/eval.py` — the deterministic scoring harness.
- `scripts/generate_eval_scorecard.py` — regenerates the committed scorecard.
- `eval/manifest.json`, `eval/labels.json` — provenance and ground truth.
- `reports/eval-scorecard.json`, `reports/eval-scorecard.md` — the scorecard.
- `tests/test_eval_scorecard.py` — pins the numbers; fails on drift.
- `decisions/DEC-MCPSEC-002-policy-corpus-over-llm-judge.md` — the prior
  determinism-over-judge decision this one is consistent with.

## requirement coverage

This DEC resolves R-MCPSEC-EVAL-001, added to
`specs/0001-mcp-security-lab/requirements.md` alongside it.

## rollback

Revert this DEC's commits: drop `mcp_security_lab/eval.py`,
`scripts/generate_eval_scorecard.py`, the `eval/` directory,
`reports/eval-scorecard.{json,md}`, `tests/test_eval_scorecard.py`, the
`R-MCPSEC-EVAL-001` rows in `requirements.md` and `traceability.md`, and
the two negation lines in `.gitignore`. Nothing depends on the eval module;
the scanner and its synthetic tests are untouched.

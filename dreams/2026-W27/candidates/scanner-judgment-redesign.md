---
target_kind: backlog_item
title: redesign scanner judgments beyond literal recall fixes
rationale: >
  The real-config scorecard exposed three weaknesses that need policy design before implementation: capability awareness, structured command parsing, and dangerous-flag semantics. Treating them as simple string patches would trade clean precision for unclear behavior.
evidence:
  - kind: eval_report
    ref: reports/eval-scorecard.md
  - kind: decision
    ref: decisions/DEC-MCPSEC-010-real-config-eval-scorecard.md
human_review_required: true
---

# redesign scanner judgments beyond literal recall fixes

The July recall patch is intentionally narrow. It repairs docker home bind mounts and unauthenticated `mcp-remote` URLs because both are directly labelled false negatives with obvious expected behavior.

The remaining weaknesses are not the same kind of work. Capability-aware labels, structured argument parsing, and dangerous-flag policy need a small design pass so the scanner does not drift from a precision gate into a broad suspicion engine.

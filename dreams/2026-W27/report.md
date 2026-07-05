# scanner redesign queue

This dream records the three scanner weaknesses deliberately left out of the July recall patch. The patch closes two concrete false negatives in the real-config scorecard; these items need a policy and judgment pass before code changes.

## candidates

- capability-aware scanner labels rather than string-only categories
- structured parser for command args instead of substring matching
- explicit dangerous-flag policy for allow/deny decisions

Each item stays human-gated. They would change the scanner's semantics, not just repair a missed literal pattern.

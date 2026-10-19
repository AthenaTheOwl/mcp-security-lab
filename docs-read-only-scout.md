# A read-only scout still crosses a trust boundary

A portfolio research agent may read public discussions, retrieve primary
sources, and prepare a local draft. A different step publishes that draft.
Keeping those operations separate gives this scanner a concrete review question:
which configured capabilities exceed the scout's assigned work?

Before connecting, export a synthetic or redacted JSON server declaration and run
the existing `scan --policy examples/policies/default.yaml --fail-on-deny` flow.
Compare the report after any tool-description or transport change with `diff`.
Keep raw declarations and both reports. A new write or shell capability should
produce a review item before a credentialed session is created.

| Boundary | Existing offline evidence | Still requires a runtime control |
|---|---|---|
| Tool descriptions | Injection phrases and declared write/shell surfaces | Restrict callable tools and actual actions |
| Credentials | Presence of auth metadata | Validate token audience, expiry and scope |
| Network | `egress` flags broad or risky allowlist entries | Enforce network policy at the sandbox or proxy |
| Publication | Descriptor and policy verdict | Separate publishing authority and explicit user authorization |

The [MCP security guidance](https://modelcontextprotocol.io/docs/draft/tutorials/security/security_best_practices)
explains token audience and passthrough risks. This scanner cannot verify the
claims inside a token or a server's honest implementation of a read-only label.
Its allow verdict is a static policy result over supplied declarations.

A review of the report grants no permission to post, to bypass an access
denial, or to share private material. Keep the scout's assignment to finding and
reading sources and writing a local evidence memo. Give a later publishing step
only the approved content and the minimum required authority.

Acceptance should include one clean read-only declaration and one changed
declaration with a write tool, plus a runtime attempt that proves the write is
unavailable. The scanner supplies the first comparison. Record the runtime test
separately and keep it explicitly not-run until it is actually exercised.

# DEC-MCPSEC-001: Config scan before runtime

## Status

Accepted

## Context

MCP clients often start local servers from source-controlled config. The security review surface starts before the process launches: command, args, env, transport, URL, auth metadata, scopes, tools, prompts, and resource descriptors.

## Decision

MCP Security Lab scans static config first. It does not connect to the server or execute any startup command during analysis.

## Consequences

The MVP can run in CI and portfolio review without granting tool execution rights. Runtime package behavior and server responses remain out of scope for the first pass.


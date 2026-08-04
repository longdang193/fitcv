# Frontend-Backend Integration MCP Setup

Context7 supplies current external-library documentation. Specmatic supplies OpenAPI discovery, examples, mocks, and contract-conformance tools. Neither server owns repository behavior, architecture, contracts, tests, or runtime truth.

## Codex Configuration

Add to `%USERPROFILE%\.codex\config.toml`:

```toml
[mcp_servers.context7]
url = "https://mcp.context7.com/mcp"

[mcp_servers.specmatic]
command = "docker"
args = ["run", "--rm", "-i", "-v", ".:/usr/src/app", "specmatic/specmatic", "mcp", "server"]
startup_timeout_sec = 120
```

Requirements:

- restart Codex after changing configuration
- keep optional API keys in private client configuration or environment variables
- run Docker Desktop before invoking Specmatic
- ensure Codex launches Specmatic from project root so `.` maps active workspace to `/usr/src/app`; otherwise replace `.` with private absolute project path

Do not commit client configuration, credentials, caches, or generated MCP state.

## Smoke Tests

### Context7

1. Resolve one dependency already pinned by current project.
2. Request documentation for pinned major/minor version.
3. Confirm returned guidance matches dependency version.

### Specmatic

1. Create temporary minimal OpenAPI file under `.tmp-tests/mcp-smoke/`.
2. Ask Specmatic to discover and validate contract.
3. Remove temporary directory.
4. Confirm `git status --short` shows no MCP state or temporary contract.

## Fallback

When either server is unavailable, continue with pinned local documentation, canonical contracts, source, tests, and existing project tooling. Do not create duplicate schemas or documentation layers.

## Removal

Delete `[mcp_servers.context7]` or `[mcp_servers.specmatic]` from private Codex configuration, then restart Codex. Remove any private cache or container image separately when no longer needed.

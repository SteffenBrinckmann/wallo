# Claude service

This folder reserves a future Claude Code CLI service. It has no runtime implementation yet and is not selectable in WALLO.

WALLO will invoke a locally installed, already authenticated `claude` executable. It will not use the Claude API, store an Anthropic API key, or configure an API URL.

## Intended transport

The adapter should follow the Codex service style: a service owns its Claude runtime, serializes exchanges (also called turns), and returns asynchronous success or error callbacks to WALLO.

- Use Claude CLI print mode (`claude -p`) with JSON output rather than parsing display text.
- Prefer `--output-format stream-json` and parse its JSON-line events for streamed assistant text, completion, errors, and session information.
- Use `--input-format stream-json` when the CLI session design supports a persistent JSON stream; otherwise invoke one JSON-output CLI process per turn while retaining the generated `--session-id` for continuity.
- Pass the selected WALLO model with `--model` when configured. Model names are CLI values, not API model configuration.

## Workspace and permissions

- Create one temporary workspace for the active Claude service, stage attachments there, and use it as the CLI working directory.
- Do not give Claude access to arbitrary user files. Any additional accessible directory must be explicitly staged first.
- Start with a restrictive permission policy. Do not use `--dangerously-skip-permissions`; define allowed or disallowed tools explicitly before enabling tool use.
- Remove the temporary workspace and end the Claude session when the user switches service or closes WALLO.

## Future configuration

The future `claude` service entry should contain only CLI-oriented options: `executable`, optional `model`, permission mode, and JSON output/input mode. It must not contain `api`, `url`, or `provider` fields.

Before starting a session, the adapter should check that `claude --version` succeeds and report a clear GUI error when Claude Code is missing or the local account is not authenticated.

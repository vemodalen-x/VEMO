# ADAPTERS — running VEMO under any harness, with any model

VEMO enforces in **three rings**. Two of them don't care what agent, model, or harness produced the change:

| ring | mechanism | binds | needs an adapter? |
|---|---|---|---|
| 1. agent loop | `enforcement/hooks/run.py` (block before the tool runs) | only harnesses with a hook API | **yes** — Claude Code wiring ships; others below |
| 2. git | `.git/hooks/pre-commit`, `pre-push` (installed by `enforcement/install.sh`) | any process that commits/pushes | no |
| 3. CI | `enforcement/ci/vemo-ci.yml` + branch protection | anything that reaches the remote | no |

**The guarantee lives in rings 2–3.** Ring 1 is fast feedback: without it the agent finds out at commit
time instead of edit time — later, but never weaker. So "does VEMO support model/agent X?" decomposes into:
governance — yes, unconditionally, via rings 2–3; ergonomics — yes if you wire ring 1.

This adapter is the `ingress` plane of the broader responsibility model; it does not own policy or evidence.
See [docs/PLATFORM.md](PLATFORM.md), and run `vemo platform --json` to inspect the topology and locally
observable delivery rings without reading source, prompts, or telemetry payloads.

## Ring-1 adapter contract (one dispatcher, any harness)

Pipe a JSON payload to stdin of `python3 enforcement/hooks/run.py <guard>`:

```json
{"tool_name": "Write",
 "tool_input": {"file_path": "src/x.py", "content": "...", "command": "..."},
 "session_id": "optional-stable-id"}
```

| guard | fire it | reads from `tool_input` |
|---|---|---|
| `edit` | before any file create/edit/delete | `file_path` (or `path`/`notebook_path`), `content`/`new_string` |
| `command` | before any shell execution | `command` |
| `budget` | before every tool call | `file_path` if any; `tool_name` decides write-vs-read |
| `stop` / `subagent-stop` | when the agent (sub-agent) finishes a turn | — |
| `session-start` | on session start | — (stdout is an orientation line for the agent) |

Contract: **exit 2 = block** (map to your harness's "deny"; stderr is the reason, feed it back to the
model), exit 0 = allow. Set `VEMO_ROOT` if the process cwd is not the repo root. Missing `session_id` and
unknown extra fields are tolerated — the minimal-payload path is part of `eval/run.py`'s conformance
checks, so the contract is executable, not aspirational. `judge-record` accepts a generic `VEMO_SESSION`
env var where no Claude session id exists.

Shipped wiring: **Claude Code** — `enforcement/install.sh` registers all six guards in
`.claude/settings.json` (see `enforcement/hooks/hooks.json`). Other harnesses (Codex CLI, Cursor, Gemini
CLI, …) expose similar pre-tool hook APIs; wire them to the table above. VEMO ships no per-product glue it
cannot test in CI — an untested adapter would be exactly the claimed-but-not-mechanized surface VEMO exists
to eliminate. Contributions welcome with an eval check per guard.

## Codex CLI (a concrete, verified ring-1 wiring)

Codex CLI ships its own hook system (`SessionStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `Stop`,
and others) configured via `.codex/hooks.json` or a `[hooks]` table in `config.toml` — the same
matcher-then-command shape as Claude Code's, so it can drive VEMO's existing dispatcher unmodified. Two
Codex-specific wrinkles versus the Claude Code wiring above:

- **Decision envelope, not a bare exit code.** Codex's default hook output is a JSON object
  (`hookSpecificOutput.permissionDecision` for `PreToolUse`, `hookSpecificOutput.decision.behavior` for
  `PermissionRequest`) — but Codex also accepts the plain **`exit 2` + stderr** contract VEMO's dispatcher
  already speaks, so no translation shim is required: register the same
  `python3 enforcement/hooks/run.py <guard>` command Codex is documented to run.
- **`PreToolUse` covers `Bash` and `apply_patch`** (Codex's file-edit tool) via `tool_input.command`; there is
  no separate `Edit`/`Write` tool name to match on the way Claude Code has one. Point Codex's `PreToolUse`
  hook at `run.py edit` for the `apply_patch` matcher and `run.py command` for the `Bash` matcher — the
  dispatcher's `target_of()` already falls back across `file_path`/`path`/`notebook_path`, so no dispatcher
  change is needed either.

Example `.codex/hooks.json` (mirrors `enforcement/hooks/hooks.json`; adjust the repo-root discovery to your
shell):

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "apply_patch",
        "hooks": [{ "type": "command",
                    "command": "python3 \"$(git rev-parse --show-toplevel)/enforcement/hooks/run.py\" edit" }] },
      { "matcher": "Bash",
        "hooks": [{ "type": "command",
                    "command": "python3 \"$(git rev-parse --show-toplevel)/enforcement/hooks/run.py\" command" }] }
    ],
    "SessionStart": [
      { "hooks": [{ "type": "command",
                    "command": "python3 \"$(git rev-parse --show-toplevel)/enforcement/hooks/run.py\" session-start" }] } ]
  }
}
```

Codex prints a one-time trust prompt for project-local hooks (`/hooks` to review/trust) — expected, not a
VEMO issue. Session provenance: Codex writes each session's transcript to
`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, and the session id is embedded in that filename — that is the
same id a Devpost-style submission asks for (see `docs/HACKATHON_PLAYBOOK.md` §4); record it in the task's
Execution Log as you go rather than reconstructing it at deadline time. `judge-record` still takes a generic
`VEMO_SESSION` env var for provenance when no Claude session id exists (see below).

## Model portability (separate question from harness portability)

- `capability.tier` is the governance contract and it is **behavioral, vendor-neutral** — classify any
  model with the rubric in `specs/capability.spec.md` §1.5. Mixed-model repos pin the tier to the weakest
  unattended model.
- `model_routing` names are advisory examples; substitute your provider's equivalents. Prefer a **judge
  from a different model family** than the worker — fresh context removes shared state, a different family
  removes shared blind spots (`capability.spec` §4).
- The gates never ask *which model* acted: receipts, provenance records, diffs, and risk tiers are all
  model-agnostic facts. That is deliberate — self-reported identity would be the same trust hole as
  self-reported test results.

## Notes
- `AGENTS.md` (the cross-harness instructions standard) is VEMO's prose entry for any agent; hookless
  agents get the same deal there: check scope before editing (`task_state.py scope-check --path <p>`),
  because ring 2 will hold you to it at commit.
- Windows: hook commands invoke `python3` — ensure it resolves (e.g. alias to `py -3`), or adjust the
  registered command; rings 2–3 are unaffected.

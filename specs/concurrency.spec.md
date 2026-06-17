# concurrency.spec — Multi-session safety (kept from Wildpanda)

> This is Wildpanda's strongest, most original piece and survives the rebuild almost intact —
> slimmed and made machine-checkable. Several agents/sessions editing one repo must not silently
> stomp each other.

## 1. Chat identity
- Each session gets `chat_id = chat-<YYYYMMDD>-<HHMM>-<3char>`, generated at first task-state write.
- Read-only sessions need no id.
- Stored authoritatively in the task front-matter `owning_chat` (machine-readable).

## 2. Heartbeat & staleness
- `heartbeat` (ISO-8601) updates on every meaningful state write (phase change, acceptance change, exec note).
- A task is **stale** when `now - heartbeat > concurrency.stale_threshold_hours` (default 4).
- Staleness is evaluated during the session-start continuity check.

## 3. Takeover protocol (hard gate — now CI-checkable)
On resume, scan live task front-matter:
1. **Same `owning_chat`** → continue.
2. **Different + stale** → ask: `[STALE] Task <id> last held by <chat> at <ts>. Take over? (Y/N)`. On yes: reassign `owning_chat`, reset heartbeat, log takeover.
3. **Different + active** → ask with a stronger prompt (force-takeover needs explicit approval).
4. **Silent takeover is forbidden** — and a pre-commit check rejects a commit whose task `owning_chat` ≠ the committing session unless a logged takeover exists. (Wildpanda asked; VEMO also checks.)

## 4. Thin index (optional)
A `tasks/_index.md` may snapshot live tasks (id, state, owning_chat, heartbeat) for fast discovery,
but the **task file front-matter is authoritative** — the index is a convenience, never the source of truth.

## 5. Why machine-check it
Wildpanda's takeover rule was prose ("must ask"). VEMO keeps the ask *and* adds a pre-commit check that
the committer owns the task — so a forgetful or misaligned session is stopped by mechanism, not etiquette.

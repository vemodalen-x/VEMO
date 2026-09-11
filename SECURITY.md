# Security model

VEMO protects one boundary: whether an AI-authored repository change is authorized and verified.

Core controls:

- scope containment for file writes and final diffs;
- credential-pattern rejection;
- external task approval for critical paths, plus category-specific approval for destructive,
  history-rewriting, and out-of-repository actions;
- approval bound to the normalized task id, scope, and risk digest, so a branch cannot widen approved scope;
- executed verification bound to the exact diff and command list;
- verification commands represented as argv arrays and executed without a shell;
- CI re-evaluation over the proposed merge range.

The authoritative security logic is `enforcement/core.py`. Hook, Git, and CI adapters must not duplicate it.

Limitations:

- VEMO is not a sandbox and cannot contain an already-compromised host.
- Local files and hooks can be altered by a hostile user; protected-branch CI is the authoritative merge guard.
- Secret detection is pattern based, not a replacement for a dedicated scanner.
- Plugins are trusted local code. Enabling one grants it normal process authority; the manifest is a discovery
  boundary, not code isolation.
- Human approval establishes intent. It does not prove the change is correct; verification still must pass.
- CI uses the evaluator from the base commit for its first no-execution decision, then uses candidate code only
  after that decision allows the range. The first 2.0 installation therefore requires an explicitly reviewed
  bootstrap merge. Require branch protection and CODEOWNERS for `vemo.json`, `vemo.task.json`, `enforcement/**`,
  and `.github/**`; a repository-local framework cannot make its server configuration immutable.

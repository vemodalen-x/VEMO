# Platform and integration support

VEMO's policy evaluator and setup service use Python's standard library. The enforcement adapters have narrower
requirements: local Git hooks use Bash, GitHub enforcement uses GitHub Actions, and the Claude Code adapter uses
Claude's `PreToolUse` hook format. Treat these as separate compatibility layers rather than one blanket claim.

## Support matrix

| Environment | Core CLI | Transactional setup | Local hooks | Authoritative merge gate | Status |
|---|---:|---:|---:|---:|---|
| Linux | Yes | Yes | Bash 4+ | GitHub Actions or another trusted CI | Verified in this repository |
| macOS | Yes, Python 3.10+ | Yes | Bash 4+ must be installed; macOS system Bash may be older | GitHub Actions or another trusted CI | Supported design; not currently covered by a macOS CI runner |
| Windows with WSL | Yes | Yes | Yes, inside WSL | GitHub Actions or another trusted CI | Recommended Windows path; not currently covered by a Windows CI runner |
| Windows with Git Bash | Core Python commands should work | Installer is available | Requires a compatible Bash/Git/Python path setup | GitHub Actions or another trusted CI | Best effort; full path and hook behavior is not verified |
| Native Windows shell only | Core Python commands should work | `start.cmd` can launch the optional UI | No native PowerShell hook adapter is shipped | GitHub Actions or another trusted CI | Partial support; use WSL for the complete local experience |
| GitHub Actions | N/A | Workflow can be installed | N/A | Yes | Canonical CI integration is shipped and tested structurally |
| Claude Code | Yes | Installed through the core installer | `PreToolUse` adapter | No; CI remains authoritative | Adapter configuration is shipped and tested structurally |
| Other AI agent or harness | Yes | Use CLI/setup service | Call `vemo check --action ...` before tools | Integrate `verify` and `check` in trusted CI | Stable CLI contract; harness-specific adapter is owned by the integrator |

"Supported design" means the implementation has no known platform-specific dependency beyond those stated.
It does not mean that this release was exercised on that operating system. The repository's current automated test
environment is Linux. Contributions adding macOS and Windows CI are welcome, but a green CI matrix must test hook
execution rather than only Python importability.

## Linux

Install Python 3.10+, Git, and Bash 4+, then use either the in-repository initializer or the setup plugin described
in [INSTALL.md](INSTALL.md). Linux is the reference and currently verified environment.

## macOS

Install a current Python and Bash (for example through the organization's approved package manager). Confirm:

```bash
python3 --version
bash --version
git --version
```

Run the normal preview/apply/check installation flow. If `bash --version` reports the older system Bash, do not
claim local-hook support until the hook interpreter is explicitly validated. Server-side CI can still be the
authoritative gate.

The optional local setup UI, which can apply reviewed installation plans, can be started from Terminal with:

```bash
./plugins/setup/ui/start.command
```

## Windows

WSL is the recommended route because it provides the same Git, Bash, path, and executable-bit model used by the
local adapters. Clone and operate the governed repository inside the WSL filesystem when possible.

The optional setup UI, which is separate from the read-only Fleet dashboard, has a native launcher:

```bat
plugins\setup\ui\start.cmd
```

Native `py -3`/`python` can run the core and setup service, but VEMO does not currently ship native PowerShell
pre-commit or pre-push adapters. On native Windows, make protected CI mandatory and treat local checks as advisory.

## GitHub repository configuration

The setup plugin installs `.github/workflows/vemo-ci.yml`; it cannot configure GitHub branch protection. An owner
must separately:

1. require pull requests for the protected branch;
2. require the `vemo` check before merge;
3. restrict changes to `vemo.json`, `vemo.task.json`, `enforcement/**`, and `.github/**` with CODEOWNERS or an
   equivalent review rule;
4. store critical-task approval variables in a protected repository or environment scope;
5. complete the first VEMO 2.0 bootstrap through a protected human-reviewed merge.

The workflow's trusted-base preflight prevents a pull request from replacing policy and immediately executing its
own verification commands. VEMO does not create repository variables, environments, reviewers, or branch rules.

## Generic agent/harness contract

An integration needs only three touchpoints:

```text
before write  -> vemo check --action write --path <repo-relative-path> --content-stdin
before command -> vemo check --action command --command <exact-command>
before handoff -> stage diff; vemo verify; stage evidence; vemo check
```

The harness must not set `VEMO_APPROVED_*` values from model output or repository content. Those values belong to a
trusted human approval service or protected CI environment. VEMO is also not a process or filesystem sandbox; pair
it with containers, virtual machines, or another isolation boundary for untrusted execution.

## Workstation control plane

The optional Fleet dashboard uses only Python's standard library and browser-native HTML/CSS/JavaScript. Linux is
the verified environment. macOS uses `plugins/fleet/ui/start.command`; Windows uses
`plugins\fleet\ui\start.cmd` and selects `py -3` or `python`. All platforms bind the server to `127.0.0.1` and
store the private registry below `$VEMO_HOME` or the user's `.vemo` directory. See
[CONTROL-PLANE.md](CONTROL-PLANE.md); macOS and Windows launchers are provided but are not currently exercised by
this repository's CI.

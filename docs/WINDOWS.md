# Windows Offline Package

The Windows x64 ZIP includes the VEMO setup UI, runtime, verification files, and a pinned PSF
Python embeddable distribution. Git for Windows remains a prerequisite. This is an unsigned ZIP
installer, not a signed EXE/MSI, Windows service, OS sandbox, or automatic Codex pre-tool adapter.

## Install

Extract the ZIP to a fresh directory. Review its SHA-256 against the separately delivered checksum,
then open PowerShell in that directory:

```powershell
.\Install.ps1
.\Install.ps1 -Apply
```

If your organization's script policy blocks unsigned scripts, use its approved signing process;
do not disable the machine policy. The script checks all listed files before copying. It installs
side-by-side under `%LOCALAPPDATA%\Programs\VEMO\<content-id>` and creates a versioned Start menu
shortcut. It requires no administrator access, does not change global PATH or Git configuration,
and never enrolls projects without a setup preview. `-NoShortcut` suppresses shortcut creation;
`-InstallRoot` selects another user-owned directory. Repeating an unchanged installation is safe.
Failed staging directories are kept for inspection. Changed installed payload is rejected.

Open **VEMO Supervision** from Start to choose an existing Git project. Setup previews conflicts,
installs the three governance layers, verifies local wiring, and supports project uninstall/rollback.
Do not automatically overwrite a project already running another task or using custom hooks.

## Runtime Boundaries

`vemo.cmd shell` opens a terminal with the private Python runtime available to child processes.
Start CLI agents from this shell if their Claude hooks require `python3` and the normal system
PATH lacks a working interpreter. Already-running desktop applications do not inherit this shell.
Git gates have their own Python fallback. The setup UI locates Git for Windows Bash instead of WSL.
Use the project's own `bin/vemo` for task commands; the package launcher operates on its framework
source and offers project selection through `setup`/`ui`/`fleet`.

Configured Claude hook events are not proof that a host has loaded them. Codex can read AGENTS.md
and is constrained by installed Git hooks, but an additional compatible adapter is required for
pre-tool blocking. Server-side authority requires successful CI and protected-branch settings on
each project. Installation alone cannot grant those guarantees.

## Upgrade And Remove

Install a new package side-by-side, then use its UI to preview each project upgrade. Project files
modified after installation are preserved as conflicts. Keep the old package until projects pass
their new installation checks. To remove supervision use **project uninstall** first; removing
the desktop package does not uninstall hooks or erase project evidence. The desktop package has
no service or registry integration: remove its versioned Start shortcut and selected package
directory after confirming it is no longer used. Do not remove a different version or project.

## Rebuild

Download the pinned archive from the [PSF Python release page](https://www.python.org/downloads/release/python-31315/).
The builder refuses any archive that does not match the official SHA-256 embedded in the script.

```powershell
python packaging/windows/build.py --runtime-zip python-3.13.15-embed-amd64.zip
```

Output is under `.vemo/dist/`, excluded from Git. `package.json` records tool-written UTC build
time, base commit, complete content hashes and runtime provenance. The content ID includes local
changes, so a base commit is not a claim that uncommitted bytes came from that commit. Hashes
detect corruption/drift; they do not authenticate an unsigned publisher.

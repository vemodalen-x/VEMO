# Changelog

## Unreleased

- Added complete installation and operating documentation for the 2.0 governance loop.
- Updated the optional setup UI help and launchers to use current plugin entry points.
- Made the lightweight installer refuse custom hook paths and conflicting managed files instead of overwriting.

## 2.0.0 — minimal kernel

- Reduced the mandatory architecture to Policy, Task, Gate, Verify, and Evidence.
- Replaced the manual six-state lifecycle with decisions derived from authorization, approval, and evidence.
- Replaced model capability tiers and change classes with `normal|critical` risk.
- Consolidated action and merge policy into `enforcement/core.py`.
- Reduced the default CLI to six commands.
- Made product reports, Fleet, setup UI, skills, review guides, and automation optional plugins; deleted the
  self-describing extension-composition subsystem rather than wrapping it in another abstraction.
- Replaced the broad platform/conformance surface with focused positive and negative contract tests.
- Added a safe 1.x task migration path without deleting historical task records.

Earlier release history remains available in Git history and tags. It is not part of the runtime contract.

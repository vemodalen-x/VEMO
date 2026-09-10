"""One distribution inventory: never ship live tasks or machine state.

The payload is the framework runtime plus what its CI conformance run executes. Files a consuming
project normally owns itself (README, LICENSE, SECURITY policy, docs/, assets/) stay in this
repository: shipping them made every project with its own README or docs/ a conflict.
"""

from pathlib import Path
from .windows import linked_path

SINGLE_FILES = (
    "AGENTS.md", ".gitattributes", "vemo.config.yaml", "VERSION",
    "tasks/_TASK_TEMPLATE.md", "bin/vemo", "bin/vemo_product.py",
    "bin/vemo_fleet.py", "bin/vemo_extensions.py",
)
DIRECTORIES = (
    "bin/vemo_setup", "bin/vemo_composition", "specs", "enforcement", "presets",
    "profiles", "extensions", "agents", "skill", "ui", "eval", "tests",
)
# Minimum executable contract, independent of whatever files remain in a damaged installation.
REQUIRED_FILES = frozenset(SINGLE_FILES) | {
    "bin/vemo_setup/__init__.py", "bin/vemo_setup/service.py", "bin/vemo_setup/payload.py",
    "bin/vemo_setup/cli.py", "bin/vemo_setup/server.py",
    "bin/vemo_setup/windows.py",
    "bin/vemo_composition/__init__.py", "bin/vemo_composition/context.py",
    "bin/vemo_composition/contracts.py", "bin/vemo_composition/loader.py",
    "enforcement/hooks/run.py", "enforcement/hooks/hooks.json",
    "enforcement/validators/task_state.py", "enforcement/validators/skill_check.py",
    "enforcement/validators/package_check.py",
    "enforcement/ci/pre-commit", "enforcement/ci/pre-push", "enforcement/ci/vemo-ci.yml",
    "extensions/index.json",
    "eval/run.py",
}


def managed_sources(source_root):
    """Enumerate portable framework files, rejecting linked source content. @codex-comment"""
    root = Path(source_root).resolve()
    files = {}
    candidates = [root / p for p in SINGLE_FILES]
    for directory in DIRECTORIES:
        candidates.extend(sorted((root / directory).rglob("*")))
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        if ("__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}
                or relative == "eval/out" or relative.startswith("eval/out/")):
            continue
        if linked_path(path) or not path.resolve().is_relative_to(root):
            raise ValueError(f"linked payload is not supported: {path}")
        if path.is_file():
            # Keep framework verification separate from the consuming application's test discovery.
            destination = "eval/" + relative if relative.startswith("tests/") else relative
            files[destination] = path
    # The consumer gets the CI source, never this repository's task history or workflow customizations.
    ci = root / "enforcement/ci/vemo-ci.yml"
    if ci.is_file():
        files[".github/workflows/vemo-ci.yml"] = ci
    return files

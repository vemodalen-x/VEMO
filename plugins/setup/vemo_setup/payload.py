"""Minimal core payload used by the optional transactional setup plugin."""

from pathlib import Path

SINGLE_FILES = (
    "AGENTS.md", "VERSION", "vemo.json", "vemo.task.example.json", "bin/vemo",
    "enforcement/core.py", "enforcement/payload.py", "enforcement/install.sh",
    "enforcement/hooks/run.py", "enforcement/hooks/hooks.json",
    "enforcement/ci/pre-commit", "enforcement/ci/pre-push", "enforcement/ci/vemo-ci.yml",
    "eval/run.py", "tests/test_core.py",
)
DIRECTORIES = ()
REQUIRED_FILES = frozenset(SINGLE_FILES)


def managed_sources(source_root):
    root = Path(source_root).resolve(); files = {}
    for relative in SINGLE_FILES:
        path = root / relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError("missing or linked core payload: " + relative)
        files[relative] = path
    files[".github/workflows/vemo-ci.yml"] = root / "enforcement/ci/vemo-ci.yml"
    return files

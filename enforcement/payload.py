"""Files in the default VEMO core installation. Plugins are never implicit payload."""

CORE_FILES = (
    "AGENTS.md",
    "VERSION",
    "vemo.json",
    "vemo.task.example.json",
    "bin/vemo",
    "enforcement/core.py",
    "enforcement/install.sh",
    "enforcement/hooks/run.py",
    "enforcement/hooks/hooks.json",
    "enforcement/ci/pre-commit",
    "enforcement/ci/pre-push",
    "enforcement/ci/vemo-ci.yml",
    "tests/test_core.py",
    "eval/run.py",
)

FORBIDDEN_CORE_PREFIXES = (
    "bin/vemo_product.py", "bin/vemo_fleet.py", "bin/vemo_setup/", "bin/vemo_composition/",
    "bin/vemo_extensions.py", "enforcement/automation/", "enforcement/validators/skill_check.py",
    "extensions/", "skill/", "agents/", "ui/", "profiles/", "presets/", "plugins/",
)

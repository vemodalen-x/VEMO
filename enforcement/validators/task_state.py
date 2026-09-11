#!/usr/bin/env python3
"""VEMO 1.x compatibility entrypoint; not part of the 2.x default payload."""

from pathlib import Path
import importlib.util
import runpy

legacy = Path(__file__).resolve().parents[2] / "plugins/legacy/task_state.py"
if __name__ == "__main__":
    runpy.run_path(str(legacy), run_name="__main__")
else:
    spec = importlib.util.spec_from_file_location("vemo_legacy_task_state", legacy)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    globals().update({name: value for name, value in vars(module).items() if not name.startswith("__")})

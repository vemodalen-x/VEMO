#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "plugins/setup"))
mode, args = sys.argv[1], sys.argv[2:]
if mode == "ui":
    from vemo_setup.server import main
else:
    from vemo_setup.cli import main
raise SystemExit(main(args, source=root))

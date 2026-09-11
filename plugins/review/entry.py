#!/usr/bin/env python3
from pathlib import Path

print((Path(__file__).resolve().parent / "governance-judge.md").read_text(encoding="utf-8"))

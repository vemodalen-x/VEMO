#!/usr/bin/env python3
"""Compatibility façade for VEMO's declarative composition package."""

import argparse
import json
import os
from pathlib import Path
import sys


BIN_DIR = Path(__file__).resolve().parent
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

from vemo_composition import (  # noqa: E402 - direct script execution needs bin/ on sys.path first
    CompositionContext,
    ContributionSpec,
    EffectScope,
    ExtensionLoader,
    ExtensionManifestError,
    ExtensionRegistry,
    HOST_CAPABILITIES,
    build_extension_report as _build_extension_report,
    discover_extension_manifests,
    validate_manifest,
)


ROOT = Path(os.environ.get("VEMO_ROOT") or Path(__file__).resolve().parents[1]).resolve()


def build_extension_report(root=None):
    """Resolve the requested checkout, defaulting to VEMO_ROOT, through the modular loader. @codex-comment"""
    return _build_extension_report(Path(root or ROOT).resolve())


def print_extension_report(report):
    """Render composition status without emitting checkout paths or manifest contents. @codex-comment"""
    summary = report["summary"]
    print("VEMO extensions | status=%s | active=%d/%d | issues=%d" % (
        summary["status"], summary["active"], summary["discovered"], summary["issues"]
    ))
    print("  host capabilities: %s" % ", ".join(report["host_capabilities"]))
    print("  load order       : %s" % (" -> ".join(report["load_order"]) or "(none)"))
    for extension in report["extensions"]:
        print("  %-28s %-8s %s" % (extension["id"], extension["state"], extension["source"]))
    for item in report["issues"]:
        subject = item.get("extension") or item.get("capability") or item.get("seam") or item.get("source")
        print("  issue            : %s%s" % (
            item["code"], " (%s)" % subject if subject else ""
        ))


def build_parser():
    """Define the read-only extension inspection/check CLI. @codex-comment"""
    parser = argparse.ArgumentParser(description="Inspect VEMO's declarative extension composition")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when composition cannot resolve")
    return parser


def main(argv=None):
    """Print the resolved composition and make failures actionable through exit status 2. @codex-comment"""
    args = build_parser().parse_args(argv)
    report = build_extension_report(ROOT)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_extension_report(report)
    return 0 if not args.check or report["summary"]["status"] == "pass" else 2


__all__ = [
    "CompositionContext", "ContributionSpec", "EffectScope", "ExtensionLoader", "ExtensionManifestError",
    "ExtensionRegistry", "HOST_CAPABILITIES", "build_extension_report", "discover_extension_manifests",
    "main", "validate_manifest",
]


if __name__ == "__main__":
    sys.exit(main())

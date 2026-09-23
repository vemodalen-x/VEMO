"""Small CLI adapter for the installation service."""

import argparse
import json
from pathlib import Path
import sys

from .service import (PRESETS, PROFILES, SetupError, apply_install, check_install,
                      plan_install, plan_uninstall, recover, uninstall)


def main(argv=None, source=None):
    parser = argparse.ArgumentParser(description="VEMO 项目安装、诊断与恢复（默认只预览）")
    parser.add_argument("action", choices=("install", "check", "uninstall", "recover"))
    parser.add_argument("target", help="现有 Git 仓库的绝对路径")
    parser.add_argument("--preset", choices=PRESETS, default="python")
    parser.add_argument("--profile", choices=PROFILES, default="solo")
    parser.add_argument("--apply", action="store_true", help="执行已选择的安装/卸载/恢复")
    parser.add_argument("--plan-id", help="安装/卸载 --apply 必填；要求项目与指定预览一致")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    source = source or Path(__file__).resolve().parents[2]
    try:
        if args.action == "install":
            payload = (apply_install(source, args.target, args.preset, args.profile, args.plan_id)
                       if args.apply else plan_install(source, args.target, args.preset, args.profile))
        elif args.action == "uninstall":
            payload = uninstall(args.target, args.plan_id) if args.apply else plan_uninstall(args.target)
        elif args.action == "recover":
            if not args.apply:
                raise SetupError("恢复会还原上次操作，请添加 --apply 执行。")
            payload = recover(args.target)
        else:
            payload = check_install(args.target)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("ready", True) else 2
    except (SetupError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

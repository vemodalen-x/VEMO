"""Previewed, transactional installation using only Python's standard library.

Transport adapters receive summaries, never backup contents. The local receipt owns only
files this installer touched; project tasks, judge records and other evidence are not payload.
"""

import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile

from .payload import DIRECTORIES, REQUIRED_FILES, SINGLE_FILES, managed_sources

PRESETS = ("python", "node", "cpp", "docs")
PROFILES = ("solo", "team", "regulated")
MANIFEST = ".vemo/install.json"
JOURNAL = ".vemo/setup-journal.json"
LOCK = ".vemo/setup.lock"
BEGIN, END = "<!-- VEMO:BEGIN -->", "<!-- VEMO:END -->"
INSTALL_FILES = REQUIRED_FILES | {"CLAUDE.md", ".gitignore", ".claude/settings.json",
                                "vemo.config.preset.yaml", ".git/hooks/pre-commit",
                                ".git/hooks/pre-push", ".github/workflows/vemo-ci.yml"}


class SetupError(Exception):
    """An actionable, bounded installation failure."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def safe_path(root, relative):
    """Reject traversals and every linked parent, including dangling links. @codex-comment"""
    rel = PurePosixPath(relative)
    if (not relative or relative != rel.as_posix() or rel.is_absolute()
            or ".." in rel.parts or "\\" in relative or ":" in relative):
        raise SetupError(f"非法安装路径：{relative}")
    path = root
    for part in rel.parts:
        path = path / part
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise SetupError(f"路径为符号链接或目录联接，请先处理：{relative}")
        if path.exists() and path != root / relative and not path.is_dir():
            raise SetupError(f"父路径不是目录：{relative}")
    return path


def run(args, root, timeout=30, input=None):
    """Use explicit argv and an isolated project environment; never execute UI text. @codex-comment"""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("VEMO_", "PYTHON")) and k != "CLAUDE_PROJECT_DIR"}
    env.update(VEMO_ROOT=str(root), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(args, cwd=root, env=env, input=input, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout)


def project_root(value):
    if not isinstance(value, str) or not value.strip():
        raise SetupError("请输入现有 Git 项目的绝对路径。")
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        raise SetupError("项目路径必须是绝对路径。")
    root = raw.resolve()
    if not root.is_dir():
        raise SetupError("项目目录不存在。请先创建项目并运行 git init。")
    if not shutil.which("git"):
        raise SetupError("未找到 Git，请安装 Git 并重新打开终端。")
    result = run(["git", "rev-parse", "--show-toplevel"], root)
    if result.returncode or Path(result.stdout.strip()).resolve() != root:
        raise SetupError("请选择 Git 仓库根目录（先在项目中运行 git init）。")
    # Shared worktree metadata and redirected hooks need a separate platform adapter.
    if not (root / ".git").is_dir() or (root / ".git").is_symlink():
        raise SetupError("此安装器暂不支持 worktree/submodule；请选择具有独立 .git 目录的仓库。")
    for relative in (MANIFEST, JOURNAL, LOCK):
        safe_path(root, relative)
    hooks = run(["git", "config", "--get", "core.hooksPath"], root)
    if hooks.returncode not in (0, 1) or hooks.stdout.strip():
        raise SetupError("检测到自定义 core.hooksPath；请先由项目维护者协调已有 Git hooks。")
    return root


def read_manifest(root):
    path = safe_path(root, MANIFEST)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Structural integrity only. A manifest written before a release added a runtime file is
        # older, not damaged: it must still support upgrade and uninstall (check_install refuses
        # to execute until the inventory is complete).
        if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
                or data["schema_version"] != 1 or not isinstance(data.get("files"), dict)
                or not data["files"]
                or data.get("preset") not in PRESETS or data.get("profile") not in PROFILES):
            raise ValueError("schema")
        for relative, row in data["files"].items():
            safe_path(root, relative)
            if not managed_path(relative):
                raise ValueError("non-payload path")
            if not isinstance(row, dict) or not valid_hash(row.get("installed_hash")):
                raise ValueError("hash")
            validate_snapshot(row["before"])
        return data
    except (ValueError, KeyError, TypeError) as exc:
        raise SetupError("安装清单损坏；请保留 .vemo/install.json 并恢复其备份。") from exc


def managed_path(relative):
    special = {"CLAUDE.md", ".gitignore", ".claude/settings.json", "vemo.config.preset.yaml",
               ".git/hooks/pre-commit", ".git/hooks/pre-push", ".github/workflows/vemo-ci.yml"}
    return relative in SINGLE_FILES or relative in special or any(relative.startswith(p + "/") for p in DIRECTORIES)


def validate_snapshot(before):
    if before is not None:
        if not isinstance(before, dict) or not isinstance(before.get("data"), str):
            raise ValueError("invalid snapshot")
        base64.b64decode(before["data"], validate=True)
        if type(before.get("mode")) is not int or not 0 <= before["mode"] <= 0o777:
            raise ValueError("invalid file mode")


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def snapshot(path):
    if not path.exists():
        return None
    if not path.is_file():
        raise SetupError(f"目标不是文件：{path.name}")
    before = {"data": base64.b64encode(path.read_bytes()).decode(),
              "mode": stat.S_IMODE(path.stat().st_mode)}
    validate_snapshot(before)
    return before


def write_file(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".vemo-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def restore(path, before):
    if before is None:
        path.unlink(missing_ok=True)
    else:
        write_file(path, base64.b64decode(before["data"], validate=True), before["mode"])


def _merge_block(original, block, begin=BEGIN, end=END):
    text = original.decode("utf-8-sig") if original else ""
    if begin in text or end in text:
        if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
            raise SetupError("VEMO 文档标记不完整，请先修复。")
        first, last = text.index(begin), text.index(end) + len(end)
        text = text[:first] + block + text[last:]
    else:
        text = text.rstrip() + ("\n\n" if text.strip() else "") + block + "\n"
    return text.encode()


def _desired(source, root, preset):
    desired = {relative: path.read_bytes() for relative, path in managed_sources(source).items()}
    if not REQUIRED_FILES.issubset(desired):
        raise SetupError("VEMO 源码包不完整；请使用完整 checkout。")
    # Only the agent entry points are merged; the project's README stays untouched.
    for filename in ("AGENTS.md", "CLAUDE.md"):
        path = safe_path(root, filename)
        original = path.read_bytes() if path.is_file() else b""
        body = ("Read AGENTS.md and follow its VEMO session routing and safety specifications."
                if filename == "CLAUDE.md" else desired[filename].decode())
        # Preserve a pre-existing identical router rather than appending it twice.
        if filename != "CLAUDE.md" and original == desired[filename]:
            continue
        desired[filename] = _merge_block(original, BEGIN + "\n" + body.rstrip() + "\n" + END)
    settings = safe_path(root, ".claude/settings.json")
    try:
        current = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
        if not isinstance(current, dict) or not isinstance(current.get("hooks", {}), dict):
            raise ValueError("settings object")
        hooks = current.setdefault("hooks", {})
        for event, entries in json.loads(desired["enforcement/hooks/hooks.json"])["hooks"].items():
            previous = hooks.setdefault(event, [])
            if not isinstance(previous, list):
                raise ValueError("hook list")
            for entry in entries:
                if entry not in previous:
                    previous.append(entry)
        desired[".claude/settings.json"] = json_bytes(current)
    except (ValueError, TypeError) as exc:
        raise SetupError(".claude/settings.json 不是有效的 hooks JSON；已保留原文件。") from exc
    ignore = safe_path(root, ".gitignore")
    desired[".gitignore"] = _merge_block(ignore.read_bytes() if ignore.is_file() else b"",
        "# VEMO:BEGIN\n/.vemo/*\n!/.vemo/judge.jsonl\n/eval/out/\n# VEMO:END", "# VEMO:BEGIN", "# VEMO:END")
    desired["vemo.config.preset.yaml"] = desired[f"presets/{preset}.yaml"]
    for name in ("pre-commit", "pre-push"):
        desired[f".git/hooks/{name}"] = desired[f"enforcement/ci/{name}"]
    return desired


def _environment(root):
    checks = [{"name": "Python", "ok": sys.version_info >= (3, 10), "detail": sys.version.split()[0],
               "runtime_source": "setup_process", "remediation": "安装 Python 3.10+ 并重新运行检查。"},
              {"name": "Git", "ok": True, "detail": run(["git", "--version"], root).stdout.strip()}]
    try:
        bash = run(["bash", "-c", 'test "${BASH_VERSINFO[0]}" -ge 4'], root)
        checks.append({"name": "Bash ≥ 4（Git 门禁）", "ok": bash.returncode == 0, "detail": "bash"})
        interpreter = run(["bash", "-c", 'python3 -I -S -c "import sys; print(sys.version.split()[0]); sys.exit(sys.version_info < (3, 10))"'], root)
        checks.append({"name": "Hooks 的 python3 ≥ 3.10", "ok": interpreter.returncode == 0,
                       "detail": interpreter.stdout.strip() or "请让 Bash 的 PATH 能找到 Python 3.10+ 的 python3 命令"})
    except (OSError, subprocess.TimeoutExpired):
        checks.append({"name": "Bash ≥ 4（Git 门禁）", "ok": False, "detail": "未找到 bash"})
    return checks


def plan_install(source, target, preset="python", profile="solo"):
    """Make the complete reviewable file plan and a content-bound approval id. @codex-comment"""
    if preset not in PRESETS or profile not in PROFILES:
        raise SetupError("请选择有效的技术栈与使用场景。")
    source, root = Path(source).resolve(), project_root(target)
    if source != root and (source / MANIFEST).exists():
        raise SetupError("请从独立的完整 VEMO 源码目录接入其他项目；当前安装来源是已受管业务项目。")
    if safe_path(root, JOURNAL).exists():
        raise SetupError("发现未完成安装，请先使用“恢复中断操作”或 setup recover。")
    manifest = read_manifest(root)
    previous = (manifest or {}).get("files", {})
    desired = _desired(source, root, preset)
    actions, conflicts = [], []
    mergeable = {"AGENTS.md", "CLAUDE.md", ".gitignore", ".claude/settings.json"}
    for relative, content in sorted(desired.items()):
        path = safe_path(root, relative)
        before = snapshot(path)
        current_hash = digest(path.read_bytes()) if before else None
        new_hash = digest(content)
        if current_hash == new_hash:
            status = "unchanged"
            if relative.startswith(".git/hooks/") and os.name != "nt" and not os.access(path, os.X_OK):
                status = "update"
        elif current_hash is None:
            status = "create"
        elif relative in previous and current_hash == previous[relative]["installed_hash"]:
            status = "update"
        elif relative not in previous and relative in mergeable:
            status = "merge"
        else:
            status = "conflict"
            conflicts.append(relative)
        actions.append({"path": relative, "status": status, "before_hash": current_hash,
                        "hash": new_hash, "mode": 0o755 if relative.startswith(".git/hooks/") or relative == "bin/vemo" else (before or {}).get("mode", 0o644)})
    environment = _environment(root)
    if any(not row["ok"] for row in environment):
        conflicts.append("缺少运行环境，请查看环境检查")
    if manifest and (manifest["preset"] != preset or manifest["profile"] != profile):
        conflicts.append("已有安装的技术栈或场景不同；请先使用原选项完成维护，配置迁移需单独审查")
    # Removed payload needs a migration contract. Do not silently leave an old executable behind.
    removed = sorted(set(previous) - set(desired))
    if removed:
        conflicts.append("新版清单移除了旧组件，需单独迁移：" + ", ".join(removed))
    revision = run(["git", "rev-parse", "HEAD"], source)
    payload = {"target": str(root), "preset": preset, "profile": profile,
               "actions": actions, "environment": environment, "conflicts": conflicts,
               "version": (source / "VERSION").read_text().strip(),
               "source_checkout_commit": revision.stdout.strip() if revision.returncode == 0 else None,
               "manifest_hash": digest(safe_path(root, MANIFEST).read_bytes()) if manifest else None}
    payload["plan_id"] = digest(json_bytes(payload))
    payload["ready"] = not conflicts
    return payload


@contextmanager
def project_lock(root):
    path = safe_path(root, LOCK)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SetupError("另一个安装操作正在运行，或中断后锁仍存在；确认进程退出后删除 .vemo/setup.lock 再恢复。") from exc
    os.close(fd)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def _rollback(root, journal):
    if (not isinstance(journal, dict) or type(journal.get("schema_version")) is not int
            or journal["schema_version"] != 1 or not isinstance(journal.get("files"), dict)
            or not journal["files"]):
        raise SetupError("恢复日志格式无效。")
    # Validate the WHOLE journal before restoring even one file.
    for relative, row in journal["files"].items():
        if not managed_path(relative) and relative != MANIFEST:
            raise SetupError("恢复日志包含非安装路径：" + relative)
        safe_path(root, relative)
        if (not isinstance(row, dict) or "after_hash" not in row
                or row["after_hash"] is not None and not valid_hash(row["after_hash"])):
            raise SetupError("恢复日志的安装后摘要无效：" + relative)
        validate_snapshot(row["before"])
    conflicts = []
    for relative, row in reversed(list(journal["files"].items())):
        path = safe_path(root, relative)
        current = digest(path.read_bytes()) if path.is_file() else None
        before = row["before"]
        old_hash = digest(base64.b64decode(before["data"])) if before else None
        if current == old_hash:
            if before and stat.S_IMODE(path.stat().st_mode) != before["mode"]:
                restore(path, before)
            continue
        if current != row["after_hash"]:
            conflicts.append(relative)
            continue
        restore(path, before)
    if conflicts:
        raise SetupError("恢复遇到后续修改，已保留文件和恢复日志：" + ", ".join(conflicts))
    safe_path(root, JOURNAL).unlink(missing_ok=True)


def _python_probes(root, hashes):
    """Run verified bytes in a private import tree; project modules are never importable. @codex-comment"""
    with tempfile.TemporaryDirectory(prefix="vemo-setup-probes-") as temporary:
        runtime = Path(temporary)
        for relative, expected_hash in hashes.items():
            if relative.startswith(("bin/", "enforcement/")):
                data = safe_path(root, relative).read_bytes()
                if digest(data) != expected_hash:
                    raise SetupError(f"已安装运行文件发生变化，未执行诊断：{relative}")
                destination = safe_path(runtime, relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
        # -I excludes cwd, the script directory and user site; -S excludes site startup hooks.
        # The extension entry adds only its private, verified bin directory. Invoke the validator
        # directly so CLI subprocess dispatch cannot drop the isolation flags.
        for name, relative, arguments in (
            ("CLI", "bin/vemo", ["--help"]),
            ("规则一致性", "enforcement/validators/task_state.py", ["selfcheck"]),
            ("能力装配", "bin/vemo_extensions.py", ["--check", "--json"]),
        ):
            try:
                result = run([sys.executable, "-I", "-S", "-B", str(runtime / relative), *arguments], root)
                yield {"name": name, "ok": result.returncode == 0, "exit_code": result.returncode,
                       "output": (result.stdout + result.stderr)[-6000:]}
            except (OSError, subprocess.TimeoutExpired) as exc:
                yield {"name": name, "ok": False, "exit_code": -1, "output": str(exc)}
        probe_root = runtime / "live-fire"
        (probe_root / "tasks").mkdir(parents=True)
        (probe_root / ".vemo").mkdir()
        (probe_root / "allowed").mkdir()
        (probe_root / "vemo.config.yaml").write_text(
            "enforcement:\n  mode: enforce\n  block_on: [scope_violation]\n"
            "  fail_closed: [scope_violation]\n  degrade_gracefully: false\n",
            encoding="utf-8",
        )
        (probe_root / "tasks" / "T-setup-live-fire.md").write_text(
            "---\nid: T-setup-live-fire\nrisk: R1\nstate: PlanCreated\n"
            "scope_in: [\"allowed/**\"]\nheartbeat: 2099-01-01T00:00:00Z\n---\n",
            encoding="utf-8",
        )
        dispatcher = runtime / "enforcement" / "hooks" / "run.py"
        validator = runtime / "enforcement" / "validators" / "task_state.py"

        def live_fire(name, target, expected_exit, remediation):
            request = json.dumps({"tool_name": "Write", "tool_input": {
                "file_path": str(probe_root / target), "content": "probe\n",
            }})
            try:
                result = run([sys.executable, "-I", "-S", "-B", str(dispatcher), "edit"],
                             probe_root, input=request)
                return {"name": name, "kind": "live_fire", "ok": result.returncode == expected_exit,
                        "exit_code": result.returncode, "expected_exit": expected_exit,
                        "output": (result.stdout + result.stderr)[-2000:], "remediation": remediation}
            except (OSError, subprocess.TimeoutExpired) as exc:
                return {"name": name, "kind": "live_fire", "ok": False, "exit_code": -1,
                        "expected_exit": expected_exit, "output": str(exc), "remediation": remediation}

        yield live_fire("Guard allow live-fire", "allowed/probe.py", 0,
                        "检查任务 scope_in 与目标路径是否一致。")
        yield live_fire("Guard deny live-fire", "outside.py", 2,
                        "确认 scope_violation 已启用且 dispatcher 使用当前任务状态。")
        disabled = validator.with_suffix(".disabled")
        validator.replace(disabled)
        try:
            yield live_fire("Guard fail-closed live-fire", "allowed/probe.py", 2,
                            "恢复 validator，并保持 scope_violation 在 fail_closed 列表中。")
        finally:
            disabled.replace(validator)


def check_install(target, expected=None):
    """Execute only known framework probes, not the consuming project's build commands. @codex-comment"""
    root = project_root(target)
    checks = []
    manifest = read_manifest(root)
    hashes = expected or {key: row["installed_hash"] for key, row in (manifest or {}).get("files", {}).items()}
    if not hashes:
        raise SetupError("没有 setup 安装记录；请先预览安装，检查不会运行未知项目脚本。")
    missing = sorted(INSTALL_FILES - set(hashes))
    if missing:
        raise SetupError("安装清单缺少运行文件记录，未执行诊断；请从完整 VEMO 源码重新预览并安装以补齐："
                         + ", ".join(missing))
    # Refuse changed executable payload before launching any of its code. Task files and project
    # source are not in this inventory and do not prevent checking a working project.
    for relative, expected_hash in hashes.items():
        if relative.startswith(("bin/", "enforcement/", "extensions/")):
            path = safe_path(root, relative)
            if not path.is_file() or digest(path.read_bytes()) != expected_hash:
                raise SetupError(f"已安装运行文件发生变化，未执行诊断：{relative}")
    checks.extend(_environment(root))
    # selfcheck only detects some malformed registrations; missing files and missing event groups
    # need an explicit installation-level probe. Preserve unrelated user settings and hooks.
    try:
        template = json.loads(safe_path(root, "enforcement/hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
        hooks = json.loads(safe_path(root, ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]
        wired = isinstance(hooks, dict) and all(
            isinstance(hooks.get(event), list) and all(entry in hooks[event] for entry in entries)
            for event, entries in template.items())
    except (OSError, ValueError, TypeError, KeyError):
        wired = False
    checks.append({"name": "Claude hooks 完整接线", "ok": wired})
    ci = safe_path(root, ".github/workflows/vemo-ci.yml")
    checks.append({"name": "CI 文件接入", "ok": ci.is_file()
                   and digest(ci.read_bytes()) == hashes.get(".github/workflows/vemo-ci.yml")})
    checks.extend(_python_probes(root, hashes))
    for name, command in (
        ("Git 提交门禁语法", ["bash", "-n", ".git/hooks/pre-commit"]),
        ("Git 推送门禁语法", ["bash", "-n", ".git/hooks/pre-push"]),
    ):
        try:
            result = run(command, root)
            checks.append({"name": name, "ok": result.returncode == 0,
                           "exit_code": result.returncode, "output": (result.stdout + result.stderr)[-6000:]})
        except (OSError, subprocess.TimeoutExpired) as exc:
            checks.append({"name": name, "ok": False, "exit_code": -1, "output": str(exc)})
    for name in ("pre-commit", "pre-push"):
        installed, source = safe_path(root, f".git/hooks/{name}"), safe_path(root, f"enforcement/ci/{name}")
        ok = installed.is_file() and source.is_file() and installed.read_bytes() == source.read_bytes()
        if os.name != "nt":
            ok = ok and os.access(installed, os.X_OK)
        checks.append({"name": name + " 接线", "ok": ok})
    return {"target": str(root), "ready": all(row["ok"] for row in checks), "checks": checks,
            "next": ["在宿主中信任项目并重启会话，确认实际 hooks 被加载。",
                     "在远端分支保护中要求 vemo 检查；本地无法证明远端已启用。",
                     "按技术栈检查 vemo.config.preset.yaml，再开始任务并运行 vemo verify。"]}


def apply_install(source, target, preset="python", profile="solo", plan_id=None):
    root = project_root(target)
    with project_lock(root):
        plan = plan_install(source, str(root), preset, profile)
        if plan_id and plan_id != plan["plan_id"]:
            raise SetupError("预览后文件已变化，请重新预览。")
        if not plan["ready"]:
            raise SetupError("安装存在冲突：" + ", ".join(plan["conflicts"]))
        desired = _desired(Path(source).resolve(), root, preset)
        previous = read_manifest(root)
        files = dict((previous or {}).get("files", {}))
        journal = {"schema_version": 1, "files": {}}
        for action in plan["actions"]:
            relative = action["path"]
            before = snapshot(safe_path(root, relative))
            if digest(desired[relative]) != action["hash"]:
                raise SetupError("源文件已变化，请重新预览。")
            if relative not in files:
                files[relative] = {"before": before, "installed_hash": action["hash"]}
            files[relative]["installed_hash"] = action["hash"]
            if action["status"] != "unchanged":
                journal["files"][relative] = {"before": before, "after_hash": action["hash"]}
        manifest = {"schema_version": 1, "version": plan["version"], "preset": preset,
                    "profile": profile, "files": files, "plan_id": plan["plan_id"],
                    "installed_at": datetime.now(timezone.utc).isoformat(),
                    "source_checkout_commit": plan["source_checkout_commit"],
                    "payload_hash": digest(json_bytes({k: digest(v) for k, v in desired.items()}))}
        # Include the receipt in the journal: interruption before its atomic replacement is recoverable.
        content = json_bytes(manifest)
        journal["files"][MANIFEST] = {"before": snapshot(safe_path(root, MANIFEST)), "after_hash": digest(content)}
        write_file(safe_path(root, JOURNAL), json_bytes(journal), 0o600)
        try:
            for action in plan["actions"]:
                if action["status"] != "unchanged":
                    destination = safe_path(root, action["path"])
                    current = digest(destination.read_bytes()) if destination.is_file() else None
                    if current != action["before_hash"]:
                        raise SetupError("安装期间文件已变化：" + action["path"])
                    write_file(safe_path(root, action["path"]), desired[action["path"]], action["mode"])
            result = check_install(str(root), {row["path"]: row["hash"] for row in plan["actions"]})
            if not result["ready"]:
                failures = [row["name"] + ": " + row.get("output", "接线不匹配") for row in result["checks"] if not row["ok"]]
                raise SetupError("安装验证失败：" + "\n".join(failures))
            manifest["verification"] = [{key: row[key] for key in ("name", "ok", "exit_code") if key in row}
                                        for row in result["checks"]]
            content = json_bytes(manifest)
            journal["files"][MANIFEST]["after_hash"] = digest(content)
            write_file(safe_path(root, JOURNAL), json_bytes(journal), 0o600)
            write_file(safe_path(root, MANIFEST), content, 0o600)
            safe_path(root, JOURNAL).unlink()
        except BaseException:
            _rollback(root, journal)
            raise
        return {"mode": "installed", "plan": plan, "verification": result,
                "receipt": MANIFEST, "payload_hash": manifest["payload_hash"]}


def plan_uninstall(target):
    root = project_root(target)
    if safe_path(root, JOURNAL).exists():
        raise SetupError("请先恢复中断操作。")
    manifest = read_manifest(root)
    if not manifest:
        raise SetupError("没有 UI/setup 安装清单；不会自动删除手动安装的文件。")
    actions = []
    for relative, row in sorted(manifest["files"].items()):
        path = safe_path(root, relative)
        current = digest(path.read_bytes()) if path.is_file() else None
        actions.append({"path": relative, "status": "restore" if row["before"] else "remove",
                        "conflict": current != row["installed_hash"]})
    result = {"target": str(root), "actions": actions,
              "manifest_hash": digest(safe_path(root, MANIFEST).read_bytes()),
              "ready": not any(row["conflict"] for row in actions)}
    result["plan_id"] = digest(json_bytes(result))
    return result


def uninstall(target, plan_id=None):
    root = project_root(target)
    with project_lock(root):
        plan = plan_uninstall(str(root))
        if plan_id and plan_id != plan["plan_id"]:
            raise SetupError("卸载预览已过期，请重新预览。")
        if not plan["ready"]:
            raise SetupError("检测到安装后修改，已保留所有文件；请先备份并处理预览中的冲突。")
        manifest = read_manifest(root)
        journal = {"schema_version": 1, "files": {}}
        for relative, row in manifest["files"].items():
            before = row["before"]
            current = snapshot(safe_path(root, relative))
            if current is None or digest(base64.b64decode(current["data"])) != row["installed_hash"]:
                raise SetupError("卸载期间文件已变化：" + relative)
            journal["files"][relative] = {"before": current,
                "after_hash": digest(base64.b64decode(before["data"])) if before else None}
        journal["files"][MANIFEST] = {"before": snapshot(safe_path(root, MANIFEST)), "after_hash": None}
        write_file(safe_path(root, JOURNAL), json_bytes(journal), 0o600)
        try:
            for relative, row in manifest["files"].items():
                path = safe_path(root, relative)
                if snapshot(path) != journal["files"][relative]["before"]:
                    raise SetupError("卸载期间文件已变化：" + relative)
                restore(path, row["before"])
            if snapshot(safe_path(root, MANIFEST)) != journal["files"][MANIFEST]["before"]:
                raise SetupError("卸载期间安装清单已变化。")
            safe_path(root, MANIFEST).unlink()
            safe_path(root, JOURNAL).unlink()
        except BaseException:
            _rollback(root, journal)
            raise
        return {"mode": "uninstalled", "target": str(root), "preserved": "任务、验收证据、judge 记录和用户原有文件已保留；空目录保留。"}


def recover(target):
    root = project_root(target)
    with project_lock(root):
        path = safe_path(root, JOURNAL)
        if not path.is_file():
            raise SetupError("没有待恢复操作。")
        try:
            journal = json.loads(path.read_text(encoding="utf-8"))
            _rollback(root, journal)
        except (ValueError, TypeError, KeyError) as exc:
            raise SetupError("恢复日志损坏，请保留日志并手动恢复备份。") from exc
    return {"mode": "recovered", "target": str(root)}

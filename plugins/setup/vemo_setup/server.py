"""Loopback-only UI adapter. One process, one token, serialized project mutations."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit
import webbrowser

from .service import (SetupError, apply_install, check_install, plan_install,
                      plan_uninstall, recover, uninstall)

MAX_BODY = 16384


class SetupServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, source, port=0):
        self.source = Path(source).resolve()
        self.token = secrets.token_urlsafe(32)
        self.previews = {}
        self.jobs = {}
        self.job_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1)
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"

    def server_close(self):
        self.executor.shutdown(wait=True)
        super().server_close()

    def start_job(self, callback):
        with self.job_lock:
            if any(row["status"] == "running" for row in self.jobs.values()):
                raise SetupError("已有操作正在运行，请等待结果。")
            self.jobs.clear()
            job_id = secrets.token_hex(12)
            self.jobs[job_id] = {"status": "running"}

        def work():
            try:
                value = {"status": "done", "result": callback()}
            except Exception as exc:
                value = {"status": "failed", "error": str(exc)}
            with self.job_lock:
                self.jobs[job_id] = value
        self.executor.submit(work)
        return {"job_id": job_id}


class Handler(BaseHTTPRequestHandler):
    server_version = "VEMO"

    def log_message(self, *_args):
        # Do not put tokens or local project paths into access logs.
        pass

    def send(self, status, payload, content_type="application/json; charset=utf-8"):
        body = json.dumps(payload, ensure_ascii=False).encode() if not isinstance(payload, bytes) else payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self, api=False):
        if self.headers.get("Host") != self.server.origin.removeprefix("http://"):
            self.send(403, {"error": "拒绝非本机 Host"})
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.origin:
            self.send(403, {"error": "拒绝跨站请求"})
            return False
        if api and not secrets.compare_digest(self.headers.get("X-Vemo-Token", ""), self.server.token):
            self.send(403, {"error": "会话已失效，请使用终端输出的完整地址重新打开页面。"})
            return False
        return True

    def do_GET(self):
        path = urlsplit(self.path).path
        if not self.authorized(api=path.startswith("/api/")):
            return
        if path == "/api/info":
            self.send(200, {"version": (self.server.source / "VERSION").read_text().strip()})
            return
        if path.startswith("/api/jobs/"):
            with self.server.job_lock:
                row = self.server.jobs.get(path.rsplit("/", 1)[-1])
            self.send(200 if row else 404, row or {"error": "操作不存在"})
            return
        files = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                 "/style.css": ("style.css", "text/css"),
                 "/help/install.html": ("help/install.html", "text/html"),
                 "/help/usage.html": ("help/usage.html", "text/html"),
                 "/help/design.html": ("help/design.html", "text/html")}
        if path not in files:
            self.send(404, {"error": "页面不存在"})
            return
        relative, mime = files[path]
        file = self.server.source / "plugins" / "setup" / "ui" / relative
        if not file.is_file():
            self.send(404, {"error": "页面不在当前源码包中"})
            return
        self.send(200, file.read_bytes(), mime + "; charset=utf-8")

    def do_POST(self):
        if not self.authorized(api=True):
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY or self.headers.get_content_type() != "application/json":
                raise SetupError("请求需要小于 16KB 的 JSON。")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise SetupError("请求必须是 JSON 对象。")
            path = urlsplit(self.path).path
            target = data.get("target", "")
            if path in ("/api/preview", "/api/uninstall-preview"):
                action = "install" if path == "/api/preview" else "uninstall"
                plan = (plan_install(self.server.source, target, data.get("preset", "python"), data.get("profile", "solo"))
                        if action == "install" else plan_uninstall(target))
                self.server.previews.clear()
                self.server.previews[plan["plan_id"]] = (action, plan)
                self.send(200, plan)
            elif path in ("/api/install", "/api/uninstall"):
                action = path.rsplit("/", 1)[-1]
                saved = self.server.previews.pop(data.get("plan_id", ""), None)
                if not saved or saved[0] != action or not saved[1]["ready"]:
                    raise SetupError("请先生成无冲突预览，再确认执行。")
                plan = saved[1]
                callback = (lambda: apply_install(self.server.source, plan["target"], plan["preset"], plan["profile"], plan["plan_id"])) if action == "install" else (lambda: uninstall(plan["target"], plan["plan_id"]))
                self.send(202, self.server.start_job(callback))
            elif path == "/api/check":
                self.send(202, self.server.start_job(lambda: check_install(target)))
            elif path == "/api/recover":
                self.send(202, self.server.start_job(lambda: recover(target)))
            else:
                self.send(404, {"error": "接口不存在"})
        except (SetupError, OSError, ValueError, TypeError) as exc:
            self.send(400, {"error": str(exc)})


def main(argv=None, source=None):
    parser = argparse.ArgumentParser(description="启动 VEMO 本地图形安装向导")
    parser.add_argument("--port", type=int, default=0, help="默认自动选择空闲端口")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("端口必须在 0–65535 之间")
    source = source or Path(__file__).resolve().parents[2]
    with SetupServer(source, args.port) as server:
        url = server.origin + "/#token=" + server.token
        print("VEMO 本地安装向导：" + url, flush=True)
        print("仅本机可访问。保持终端打开；按 Ctrl+C 停止。", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0

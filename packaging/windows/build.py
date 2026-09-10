"""Build an offline Windows ZIP with a pinned PSF embeddable runtime."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bin"))
from vemo_setup.payload import managed_sources

PYTHON_VERSION = "3.13.15"
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
PYTHON_SHA256 = "d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(runtime_zip, output):
    raw = Path(runtime_zip).read_bytes()
    if sha(raw) != PYTHON_SHA256:
        raise ValueError("Python runtime SHA-256 does not match the official pinned distribution")
    files = {"framework/" + name: path.read_bytes() for name, path in managed_sources(ROOT).items()}
    for name in ("LICENSE", "README.md", "docs/INSTALL.md", "docs/WINDOWS.md"):
        files["framework/" + name] = (ROOT / name).read_bytes()
    for name in ("Install.ps1", "vemo.cmd"):
        files[name] = (ROOT / "packaging/windows" / name).read_bytes()
    with zipfile.ZipFile(runtime_zip) as runtime:
        for info in runtime.infolist():
            if info.is_dir():
                continue
            if "/" in info.filename or "\\" in info.filename or ":" in info.filename:
                raise ValueError("Unexpected nested Python archive member")
            files["runtime/" + info.filename] = runtime.read(info)
    # Bash hooks use python3; neither launcher is added to the user's global PATH.
    files["runtime/python3.exe"] = files["runtime/python.exe"]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    inventory = {name: sha(data) for name, data in sorted(files.items())}
    content_id = sha(json.dumps(inventory, sort_keys=True).encode())[:16]
    manifest = {"schema_version": 1, "build_id": content_id,
                "framework_version": (ROOT / "VERSION").read_text().strip(),
                "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "base_commit": commit, "python_version": PYTHON_VERSION,
                "python_url": PYTHON_URL, "python_sha256": PYTHON_SHA256,
                "files": inventory}
    files["package.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"VEMO-{manifest['framework_version']}-windows-x64-{content_id}.zip"
    if archive.exists():
        raise FileExistsError(f"Refusing to replace existing release artifact: {archive}")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as package:
        for name, data in sorted(files.items()):
            package.writestr(name, data)
    checksum = sha(archive.read_bytes())
    archive.with_suffix(".zip.sha256").write_text(checksum + "  " + archive.name + "\n", encoding="ascii")
    return {"archive": str(archive), "sha256": checksum, "build_id": content_id, "files": len(inventory)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-zip", required=True)
    parser.add_argument("--output", default=str(ROOT / ".vemo/dist"))
    args = parser.parse_args()
    print(json.dumps(build(args.runtime_zip, args.output), indent=2))

"""Fail closed on incomplete, non-portable or corrupt framework payloads (not a CVE scanner)."""

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bin"))
from vemo_setup.payload import REQUIRED_FILES, managed_sources


def check_source(root):
    files = managed_sources(root)
    missing = REQUIRED_FILES - set(files)
    if missing:
        raise ValueError("Missing runtime files: " + ", ".join(sorted(missing)))
    for name, path in files.items():
        if path.suffix.lower() in {".exe", ".dll", ".key", ".pem", ".pfx"} or path.name == ".env":
            raise ValueError("Unexpected binary or credential container: " + name)
        if path.suffix == ".py" or name == "bin/vemo":
            ast.parse(path.read_text(encoding="utf-8"), filename=name)
    return {"source_files": len(files), "required_files": len(REQUIRED_FILES), "status": "pass"}


def check_archive(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP members")
        for name in names:
            posix = PurePosixPath(name)
            if posix.is_absolute() or ".." in posix.parts or "\\" in name or ":" in name:
                raise ValueError("Unsafe ZIP member: " + name)
        manifest = json.loads(archive.read("package.json"))
        if manifest.get("schema_version") != 1:
            raise ValueError("Invalid package schema")
        files = manifest["files"]
        required = {"framework/" + name for name in REQUIRED_FILES} | {"Install.ps1", "vemo.cmd", "runtime/python.exe"}
        if not required.issubset(files) or set(names) != set(files) | {"package.json"}:
            raise ValueError("Package inventory mismatch")
        for name, expected in files.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Package checksum mismatch: " + name)
            if "/tasks/T-" in name or "/.vemo/" in name or "/.git/" in name:
                raise ValueError("Private task or machine state in package: " + name)
    return {"archive_files": len(files), "status": "pass"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive")
    args = parser.parse_args()
    try:
        print(json.dumps(check_archive(args.archive) if args.archive else check_source(ROOT), sort_keys=True))
    except (OSError, ValueError, KeyError, SyntaxError, zipfile.BadZipFile) as exc:
        print("Package check failed: " + str(exc), file=sys.stderr)
        sys.exit(1)

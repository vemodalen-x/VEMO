"""Locate the native Git shell instead of the Windows WSL launcher."""

import os
from pathlib import Path
import shutil
import stat


def linked_path(path):
    """Recognize junctions on Python 3.10/3.11 as well as newer pathlib."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def git_bash():
    if os.name != "nt":
        return shutil.which("bash") or "bash"
    git = shutil.which("git")
    if git:
        for parent in Path(git).resolve().parents:
            candidate = parent / "bin" / "bash.exe"
            if candidate.is_file():
                return str(candidate)
    raise FileNotFoundError("Git for Windows Bash was not found beside git.exe")

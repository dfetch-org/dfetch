"""Generic python utilities."""

import os
import shutil
import stat
from contextlib import contextmanager
from typing import Any, Generator, List


def _remove_readonly(func: Any, path: str, _: Any) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def safe_rm(path: str) -> None:
    """Delete an file or directory safely."""
    if os.path.isdir(path):
        safe_rmtree(path)
    else:
        os.remove(path)


def safe_rmtree(path: str) -> None:
    """Delete an entire directory and all its subfolders and files."""
    try:
        shutil.rmtree(path, onerror=_remove_readonly)
    except PermissionError as exc:
        raise RuntimeError(
            f"File or directory in use, cannot remove files at {path}, remove manually and retry"
        ) from exc


@contextmanager
def in_directory(path: str) -> Generator[str, None, None]:
    """Work temporarily in a given directory."""
    pwd = os.getcwd()
    if not os.path.isdir(path):
        path = os.path.dirname(path)
    os.chdir(path)
    yield path
    os.chdir(pwd)


def find_file(name: str, path: str = ".") -> List[str]:
    """Find all files with a specific name recursively in a directory."""
    return [
        os.path.join(root, name) for root, _, files in os.walk(path) if name in files
    ]

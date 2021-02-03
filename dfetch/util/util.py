"""Generic python utilities."""

import hashlib
import os
import shutil
import stat
from contextlib import contextmanager
from typing import Any, Generator, List, Optional


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


def hash_directory(path: str, skiplist: Optional[List[str]]) -> str:
    """Hash a directory with all its files."""
    digest = hashlib.sha256()

    for root, _, files in os.walk(path):
        for name in files:
            if not skiplist or name not in skiplist:
                file_path = os.path.join(root, name)

                # Hash the path and add to the digest to account for empty files/directories
                digest.update(hashlib.sha256(name.encode()).digest())

                if os.path.isfile(file_path):
                    with open(file_path, "rb") as f_obj:
                        while True:
                            buf = f_obj.read(1024 * 1024)
                            if not buf:
                                break
                            digest.update(buf)

    return digest.hexdigest()

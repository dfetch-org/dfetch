"""Generic python utilities."""

import fnmatch
import hashlib
import os
import shutil
import stat
from contextlib import contextmanager
from typing import Any, Generator, Iterator, List, Optional


def _remove_readonly(func: Any, path: str, _: Any) -> None:
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise  # pylint: disable=misplaced-bare-raise


def find_non_matching_files(directory: str, pattern: str) -> Iterator[str]:
    """Find files NOT matching the given pattern."""
    for root, _, files in os.walk(directory):
        for basename in files:
            if not fnmatch.fnmatch(basename, pattern):
                yield os.path.join(root, basename)


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


@contextmanager
def catch_runtime_exceptions(
    exc_list: Optional[List[str]] = None,
) -> Generator[List[str], None, None]:
    """Catch all runtime errors and add it to list of strings."""
    exc_list = exc_list or []
    try:
        yield exc_list
    except RuntimeError as exc:
        exc_list += [str(exc)]


@contextmanager
def prefix_runtime_exceptions(
    prefix: str,
) -> Generator[None, None, None]:
    """Prefix any runtime error with given string."""
    try:
        yield None
    except RuntimeError as exc:
        raise RuntimeError(f"{prefix}: {exc}") from exc


def find_file(name: str, path: str = ".") -> List[str]:
    """Find all files with a specific name recursively in a directory."""
    return [
        os.path.join(root, name) for root, _, files in os.walk(path) if name in files
    ]


def hash_directory(path: str, skiplist: Optional[List[str]]) -> str:
    """Hash a directory with all its files."""
    digest = hashlib.md5()  # nosec
    skiplist = skiplist or []

    for root, _, files in os.walk(path):
        for name in files:
            if name not in skiplist:
                file_path = os.path.join(root, name)

                # Hash the path and add to the digest to account for empty files/directories
                digest.update(hashlib.md5(name.encode()).digest())  # nosec
                digest = hash_file(file_path, digest)

    return digest.hexdigest()


def hash_file(file_path: str, digest: "hashlib._Hash") -> "hashlib._Hash":
    """Hash the file at path."""
    if os.path.isfile(file_path):
        with open(file_path, "rb") as f_obj:
            buf = f_obj.read(1024 * 1024)
            while buf:
                digest.update(buf)
                buf = f_obj.read(1024 * 1024)

    return digest

"""Generic python utilities."""

import fnmatch
import hashlib
import os
import re
import shutil
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Iterator, List, Optional, Sequence, Union

from _hashlib import HASH


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


def find_matching_files(directory: str, patterns: Sequence[str]) -> Iterator[Path]:
    """Find files matching the given pattern."""
    directory_path = Path(directory)

    for pattern in patterns:
        if pattern.startswith("/"):
            pattern = pattern[1:]
        matching_paths = directory_path.rglob(pattern)

        for path in matching_paths:
            yield Path(path)


def safe_rm(path: Union[str, Path]) -> None:
    """Delete an file or directory safely."""
    if os.path.isdir(path):
        safe_rmtree(str(path))
    else:
        os.remove(path)


def safe_rmtree(path: str) -> None:
    """Delete an entire directory and all its subfolders and files."""
    try:
        shutil.rmtree(  # pylint: disable=deprecated-argument
            path, onerror=_remove_readonly
        )
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
    try:
        yield path
    finally:
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


def recursive_listdir(directory):
    """List all entries in the current directory."""
    entries = os.listdir(directory)

    for entry in entries:
        full_path = os.path.join(directory, entry)

        if os.path.isdir(full_path):
            # If the entry is a directory, recurse into it
            yield from recursive_listdir(full_path)
        else:
            # If the entry is a file, yield its path
            yield full_path


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


def hash_file(file_path: str, digest: HASH) -> HASH:
    """Hash the file at path."""
    if os.path.isfile(file_path):
        with open(file_path, "rb") as f_obj:
            buf = f_obj.read(1024 * 1024)
            while buf:
                digest.update(buf)
                buf = f_obj.read(1024 * 1024)

    return digest


def hash_file_normalized(file_path: str) -> "hashlib._Hash":
    """
    hash a file's contents, ignoring line feed differences (line ending normalization)
    """
    digest = hashlib.sha1(usedforsecurity=False)

    if os.path.isfile(file_path):
        normalize_re = re.compile(b"\r\n|\r")

        with open(file_path, "rb") as f_obj:
            buf = f_obj.read(1024 * 1024)
            while buf:
                normalized_buf = normalize_re.sub(b"\n", buf)
                digest.update(normalized_buf)  # nosec
                buf = f_obj.read(1024 * 1024)

    return digest

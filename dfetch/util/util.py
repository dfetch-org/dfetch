"""Generic python utilities."""

import fnmatch
import hashlib
import os
import shutil
import stat
from collections.abc import Generator, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from _hashlib import HASH

#: Glob patterns used to identify license files by filename.
LICENSE_GLOBS = ["licen[cs]e*", "copying*", "copyright*"]


def is_license_file(filename: str) -> bool:
    """Return *True* when *filename* matches a known license file pattern."""
    return any(fnmatch.fnmatch(filename.lower(), pattern) for pattern in LICENSE_GLOBS)


def _copy_entry(src_entry: str, dest_entry: str) -> None:
    """Copy a single file or directory *src_entry* to *dest_entry*."""
    if os.path.isdir(src_entry):
        shutil.copytree(src_entry, dest_entry)
    else:
        shutil.copy2(src_entry, dest_entry)


def copy_directory_contents(src_dir: str, dest_dir: str) -> None:
    """Copy every entry in *src_dir* directly into *dest_dir*.

    Directories are copied recursively; files are copied with metadata.
    """
    for entry_name in os.listdir(src_dir):
        _copy_entry(
            os.path.join(src_dir, entry_name),
            os.path.join(dest_dir, entry_name),
        )


def copy_src_subset(
    src_root: str, dest_dir: str, src: str, keep_licenses: bool
) -> None:
    """Copy a *src* sub-path from *src_root* into *dest_dir*.

    When *src* is a directory, its contents are copied flat into *dest_dir*.
    When *src* is a single file, that file is copied into *dest_dir*.
    If *keep_licenses* is ``True``, any license files found directly in
    *src_root* are also copied regardless of the *src* filter.

    Raises:
        RuntimeError: When *src* does not exist inside *src_root*.
    """
    resolved_src_root = os.path.realpath(src_root)
    src_path = os.path.join(src_root, src)
    resolved_src_path = os.path.realpath(src_path)
    if os.path.commonpath([resolved_src_root, resolved_src_path]) != resolved_src_root:
        raise RuntimeError(f"src {src!r} escapes the source root")
    if os.path.isdir(resolved_src_path):
        copy_directory_contents(resolved_src_path, dest_dir)
    elif os.path.isfile(resolved_src_path):
        shutil.copy2(
            resolved_src_path,
            os.path.join(dest_dir, os.path.basename(resolved_src_path)),
        )
    else:
        raise RuntimeError(f"src {src!r} was not found in the extracted archive")

    if keep_licenses:
        for entry_name in os.listdir(src_root):
            full_path = os.path.join(src_root, entry_name)
            if os.path.isfile(full_path) and is_license_file(entry_name):
                shutil.copy2(full_path, os.path.join(dest_dir, entry_name))


def prune_files_by_pattern(directory: str, patterns: Sequence[str]) -> None:
    """Remove files and directories in *directory* matching *patterns*.

    License files are never removed even when they match a pattern.
    """
    for file_or_dir in find_matching_files(directory, patterns):
        if not (file_or_dir.is_file() and is_license_file(file_or_dir.name)):
            safe_rm(file_or_dir)


def _remove_readonly(func: Any, path: str, _: Any) -> None:
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise  # pylint: disable=misplaced-bare-raise


def find_non_matching_files(directory: str, patterns: Sequence[str]) -> Iterator[str]:
    """Find files NOT matching the given patterns."""
    for root, _, files in os.walk(directory):
        for basename in files:
            if not any(fnmatch.fnmatch(basename, pattern) for pattern in patterns):
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


def safe_rm(path: str | Path) -> None:
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
def in_directory(path: str | Path) -> Generator[str, None, None]:
    """Work temporarily in a given directory."""
    pwd = os.getcwd()
    if not os.path.isdir(path):
        path = os.path.dirname(path)
    os.chdir(path)
    try:
        yield str(path)
    finally:
        os.chdir(pwd)


@contextmanager
def catch_runtime_exceptions(
    exc_list: list[str] | None = None,
) -> Generator[list[str], None, None]:
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


def find_file(name: str, path: str = ".") -> list[str]:
    """Find all files with a specific name recursively in a directory."""
    return [
        os.path.join(root, name) for root, _, files in os.walk(path) if name in files
    ]


def hash_directory(path: str, skiplist: list[str] | None) -> str:
    """Hash a directory with all its files.

    Files are visited in a deterministic, sorted order so that the hash is
    identical regardless of filesystem traversal order.  The relative path of
    each file (not just its basename) is included in the hash so that files
    with the same name in different sub-directories are distinguished.
    """
    digest = hashlib.md5(usedforsecurity=False)
    skiplist = skiplist or []

    for root, dirs, files in os.walk(path):
        dirs.sort()  # Ensure deterministic directory traversal order
        for name in sorted(files):
            if name not in skiplist:
                file_path = os.path.join(root, name)
                rel_path = os.path.relpath(file_path, path)

                # Hash the relative path to account for empty files/directories
                # and to distinguish same-named files in different sub-directories
                digest.update(
                    hashlib.md5(rel_path.encode(), usedforsecurity=False).digest()
                )
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


def always_str_list(data: str | list[str]) -> list[str]:
    """Convert a string or list of strings into a list of strings.

    Args:
        data: A string or list of strings.

    Returns:
        A list of strings. Empty strings are converted to empty lists.
    """
    return data if not isinstance(data, str) else [data] if data else []


def str_if_possible(data: list[str]) -> str | list[str]:
    """Convert a single-element list to a string, otherwise keep as list.

    Args:
        data: A list of strings.

    Returns:
        A single string if the list has exactly one element, an empty string
        if the list is empty, otherwise the original list.
    """
    return "" if not data else data[0] if len(data) == 1 else data


def resolve_absolute_path(path: str | Path) -> Path:
    """Return a guaranteed absolute Path, resolving symlinks.

    Args:
        path: A string or Path to resolve.

    Notes:
        - Uses os.path.realpath for reliable absolute paths across platforms.
        - Handles Windows drive-relative paths and expands '~'.
    """
    return Path(os.path.realpath(Path(path).expanduser()))

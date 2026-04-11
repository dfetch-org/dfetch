"""Steps for archive-based feature tests."""

# pylint: disable=function-redefined, missing-function-docstring, import-error, not-callable
# pyright: reportRedeclaration=false, reportAttributeAccessIssue=false, reportCallIssue=false

import hashlib
import io
import os
import pathlib
import tarfile
import zipfile

from behave import given  # pylint: disable=no-name-in-module


def _file_digest(path: str, constructor) -> str:
    """Return the hex digest of *path* using the given hashlib *constructor*."""
    h = constructor()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_tar_gz(archive_path: str, name: str, files: list[dict]) -> None:
    """Create a .tar.gz archive with files nested under a top-level <name>/ directory."""
    with tarfile.open(archive_path, "w:gz") as tar:
        for file in files:
            content = f"Generated file {file['path']}\n".encode()
            member_path = f"{name}/{file['path']}"
            info = tarfile.TarInfo(name=member_path)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))


def create_zip(archive_path: str, name: str, files: list[dict]) -> None:
    """Create a .zip archive with files nested under a top-level <name>/ directory."""
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            content = f"Generated file {file['path']}\n"
            member_path = f"{name}/{file['path']}"
            zf.writestr(member_path, content)


def add_symlink_to_tar_gz(
    archive_path: str, name: str, symlink_path: str, symlink_target: str
) -> None:
    """Append a symlink member to an existing .tar.gz archive.

    Rewrites the archive because gzip does not support append mode in Python's tarfile.
    """
    existing: list[tuple[tarfile.TarInfo, bytes | None]] = []
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            fobj = tar.extractfile(member)
            existing.append((member, fobj.read() if fobj else None))

    with tarfile.open(archive_path, "w:gz") as tar:
        for member, data in existing:
            tar.addfile(member, io.BytesIO(data) if data is not None else None)
        info = tarfile.TarInfo(name=f"{name}/{symlink_path}")
        info.type = tarfile.SYMTYPE
        info.linkname = symlink_target
        tar.addfile(info)


def _archive_url(context, filename: str) -> str:
    """Build the archive URL in the same format used by apply_manifest_substitutions.

    apply_manifest_substitutions produces ``file:///`` + absolute path, which for an
    absolute path like ``/tmp/...`` yields four slashes (``file:////tmp/...``).
    We must match that format so placeholder substitution works in SBOM assertions.

    :func:`pathlib.Path.as_posix` is used instead of :func:`str.split`/join so
    that mixed separators (e.g. on Windows) are normalised correctly.
    """
    server_posix = pathlib.Path(context.remotes_dir_path).as_uri()
    return f"{server_posix}/{filename}"


def _create_archive(context, name: str, extension: str) -> None:
    """Create an archive of the given *extension* in the remote server directory."""
    server_path = context.remotes_dir_path
    pathlib.Path(server_path).mkdir(parents=True, exist_ok=True)

    filename = f"{name}{extension}"
    archive_path = os.path.join(server_path, filename)
    files = list(context.table) if context.table else [{"path": "README.md"}]

    if extension == ".tar.gz":
        create_tar_gz(archive_path, name, files)
    elif extension == ".zip":
        create_zip(archive_path, name, files)
    else:
        raise ValueError(f"Unsupported archive extension: {extension!r}")

    context.archive_sha256 = _file_digest(archive_path, hashlib.sha256)
    context.archive_sha384 = _file_digest(archive_path, hashlib.sha384)
    context.archive_sha512 = _file_digest(archive_path, hashlib.sha512)
    context.archive_url = _archive_url(context, filename)


@given('an archive "{name}.tar.gz" with the files')
@given('an archive "{name}.tar.gz"')
def step_impl(context, name):
    _create_archive(context, name, ".tar.gz")


@given('an archive "{name}.zip" with the files')
@given('an archive "{name}.zip"')
def step_impl(context, name):
    _create_archive(context, name, ".zip")


@given(
    'the archive "{name}.tar.gz" contains a symlink "{symlink_path}" pointing to "{symlink_target}"'
)
def step_impl(context, name, symlink_path, symlink_target):
    server_path = context.remotes_dir_path
    archive_path = os.path.join(server_path, f"{name}.tar.gz")
    add_symlink_to_tar_gz(archive_path, name, symlink_path, symlink_target)
    context.archive_sha256 = _file_digest(archive_path, hashlib.sha256)
    context.archive_sha384 = _file_digest(archive_path, hashlib.sha384)
    context.archive_sha512 = _file_digest(archive_path, hashlib.sha512)

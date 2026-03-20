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

from dfetch.util.util import in_directory


def compute_sha256(path: str) -> str:
    """Compute the SHA-256 hash of a file."""
    h = hashlib.sha256()
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


@given('an archive "{name}.tar.gz" with the files')
@given('an archive "{name}.tar.gz"')
def step_impl(context, name):
    server_path = context.remotes_dir_path
    pathlib.Path(server_path).mkdir(parents=True, exist_ok=True)

    archive_path = os.path.join(server_path, f"{name}.tar.gz")
    files = list(context.table) if context.table else [{"path": "README.md"}]
    create_tar_gz(archive_path, name, files)

    context.archive_sha256 = compute_sha256(archive_path)
    context.archive_url = pathlib.Path(archive_path).as_uri()


@given('an archive "{name}.zip" with the files')
@given('an archive "{name}.zip"')
def step_impl(context, name):
    server_path = context.remotes_dir_path
    pathlib.Path(server_path).mkdir(parents=True, exist_ok=True)

    archive_path = os.path.join(server_path, f"{name}.zip")
    files = list(context.table) if context.table else [{"path": "README.md"}]
    create_zip(archive_path, name, files)

    context.archive_sha256 = compute_sha256(archive_path)
    context.archive_url = pathlib.Path(archive_path).as_uri()

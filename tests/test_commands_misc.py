"""Tests for small command modules: environment, init, validate, format_patch, update_patch."""

# mypy: ignore-errors
# flake8: noqa

import argparse
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from dfetch.commands.environment import Environment
from dfetch.commands.format_patch import FormatPatch, _determine_target_patch_type
from dfetch.commands.init import Init
from dfetch.commands.update_patch import UpdatePatch
from dfetch.commands.validate import Validate
from dfetch.project.superproject import NoVcsSuperProject
from tests.manifest_mock import mock_manifest

# ============================
# Environment command
# ============================


def test_environment_prints_version():
    """Environment.__call__ logs the dfetch version."""
    env = Environment()
    with patch(
        "dfetch.commands.environment.newer_version_available", return_value=None
    ):
        with patch("dfetch.commands.environment.logger") as mock_logger:
            with patch("dfetch.commands.environment.SUPPORTED_SUBPROJECT_TYPES", []):
                env(argparse.Namespace())
                mock_logger.print_report_line.assert_called()


def test_environment_logs_newer_version_when_available():
    """Environment logs a notice when a newer version is available."""
    env = Environment()
    with patch(
        "dfetch.commands.environment.newer_version_available", return_value="99.0.0"
    ):
        with patch("dfetch.commands.environment.logger") as mock_logger:
            with patch("dfetch.commands.environment.SUPPORTED_SUBPROJECT_TYPES", []):
                env(argparse.Namespace())
                mock_logger.print_newer_version_notice.assert_called_once_with("99.0.0")


def test_environment_no_newer_version_notice():
    """When no newer version exists, print_newer_version_notice is not called."""
    env = Environment()
    with patch(
        "dfetch.commands.environment.newer_version_available", return_value=None
    ):
        with patch("dfetch.commands.environment.logger") as mock_logger:
            with patch("dfetch.commands.environment.SUPPORTED_SUBPROJECT_TYPES", []):
                env(argparse.Namespace())
                mock_logger.print_newer_version_notice.assert_not_called()


def test_environment_calls_list_tool_info_for_each_project_type():
    """Environment calls list_tool_info on every supported project type."""
    env = Environment()
    mock_type = Mock()
    with patch(
        "dfetch.commands.environment.newer_version_available", return_value=None
    ):
        with patch("dfetch.commands.environment.logger"):
            with patch(
                "dfetch.commands.environment.SUPPORTED_SUBPROJECT_TYPES",
                [mock_type],
            ):
                env(argparse.Namespace())
    mock_type.list_tool_info.assert_called_once()


def test_environment_create_menu():
    """Environment.create_menu registers the 'environment' subcommand."""
    subparsers = argparse.ArgumentParser().add_subparsers()
    Environment.create_menu(subparsers)
    assert "environment" in subparsers.choices


# ============================
# Init command
# ============================


def test_init_creates_manifest_when_absent():
    """Init copies the template when dfetch.yaml does not exist."""
    init = Init()
    with patch("os.path.isfile", return_value=False):
        with patch(
            "dfetch.commands.init.shutil.copyfile", return_value="/tmp/dfetch.yaml"
        ) as mock_copy:
            with patch("dfetch.commands.init.TEMPLATE_PATH") as mock_template:
                mock_template.__enter__ = Mock(return_value="/path/to/template.yaml")
                mock_template.__exit__ = Mock(return_value=False)
                with patch("dfetch.commands.init.logger"):
                    init(argparse.Namespace())
                mock_copy.assert_called_once()


def test_init_does_not_overwrite_existing_manifest():
    """Init logs a warning and returns early when dfetch.yaml already exists."""
    init = Init()
    with patch("os.path.isfile", return_value=True):
        with patch("dfetch.commands.init.shutil.copyfile") as mock_copy:
            with patch("dfetch.commands.init.logger") as mock_logger:
                init(argparse.Namespace())
                mock_copy.assert_not_called()
                mock_logger.warning.assert_called_once()


def test_init_create_menu():
    """Init.create_menu registers the 'init' subcommand."""
    subparsers = argparse.ArgumentParser().add_subparsers()
    Init.create_menu(subparsers)
    assert "init" in subparsers.choices


# ============================
# Validate command
# ============================


def test_validate_calls_manifest_from_file():
    """Validate loads and validates the manifest without errors."""
    validate = Validate()
    with patch(
        "dfetch.commands.validate.find_manifest", return_value="/some/dfetch.yaml"
    ):
        with patch("dfetch.commands.validate.Manifest.from_file") as mock_from_file:
            with patch("dfetch.commands.validate.logger") as mock_logger:
                with patch("os.path.relpath", return_value="dfetch.yaml"):
                    validate(argparse.Namespace())
                mock_from_file.assert_called_once_with("/some/dfetch.yaml")


def test_validate_prints_valid():
    """Validate logs a 'valid' report line for the manifest."""
    validate = Validate()
    with patch(
        "dfetch.commands.validate.find_manifest", return_value="/some/dfetch.yaml"
    ):
        with patch("dfetch.commands.validate.Manifest.from_file"):
            with patch("dfetch.commands.validate.logger") as mock_logger:
                with patch("os.path.relpath", return_value="dfetch.yaml"):
                    validate(argparse.Namespace())
                    mock_logger.print_report_line.assert_called_once_with(
                        "dfetch.yaml", "valid"
                    )


def test_validate_create_menu():
    """Validate.create_menu registers the 'validate' subcommand."""
    subparsers = argparse.ArgumentParser().add_subparsers()
    Validate.create_menu(subparsers)
    assert "validate" in subparsers.choices


# ============================
# FormatPatch helpers
# ============================


def test_determine_target_patch_type_git():
    """Git subprojects get PatchType.GIT."""
    from dfetch.project.gitsubproject import GitSubProject
    from dfetch.vcs.patch import PatchType

    sub = Mock(spec=GitSubProject)
    assert _determine_target_patch_type(sub) == PatchType.GIT


def test_determine_target_patch_type_svn():
    """SVN subprojects get PatchType.SVN."""
    from dfetch.project.svnsubproject import SvnSubProject
    from dfetch.vcs.patch import PatchType

    sub = Mock(spec=SvnSubProject)
    assert _determine_target_patch_type(sub) == PatchType.SVN


def test_determine_target_patch_type_plain():
    """Other subprojects get PatchType.PLAIN."""
    from dfetch.project.subproject import SubProject
    from dfetch.vcs.patch import PatchType

    sub = Mock()
    # not a GitSubProject or SvnSubProject
    assert _determine_target_patch_type(sub) == PatchType.PLAIN


def test_format_patch_no_patch_logs_warning():
    """FormatPatch logs a warning when the project has no patch file configured."""
    format_patch = FormatPatch()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = Mock()
    superproject.manifest = manifest
    superproject.root_directory = Path("/tmp")

    with patch(
        "dfetch.commands.format_patch.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.format_patch.in_directory"):
            with patch(
                "dfetch.commands.format_patch.dfetch.project.create_sub_project"
            ) as mock_create:
                with patch("dfetch.commands.format_patch.check_no_path_traversal"):
                    with patch("pathlib.Path.mkdir"):
                        with patch(
                            "dfetch.commands.format_patch.logger"
                        ) as mock_logger:
                            mock_sub = Mock()
                            mock_sub.patch = []  # no patch
                            mock_create.return_value = mock_sub

                            args = argparse.Namespace(projects=[], output_directory=".")
                            format_patch(args)

                            mock_logger.print_warning_line.assert_called_once()
                            call_args = mock_logger.print_warning_line.call_args[0]
                            assert "no patch file" in call_args[1]


def test_format_patch_runtime_error_raises():
    """FormatPatch raises RuntimeError at end if any project raises RuntimeError."""
    format_patch = FormatPatch()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = Mock()
    superproject.manifest = manifest
    superproject.root_directory = Path("/tmp")

    with patch(
        "dfetch.commands.format_patch.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.format_patch.in_directory"):
            with patch(
                "dfetch.commands.format_patch.dfetch.project.create_sub_project"
            ) as mock_create:
                with patch("dfetch.commands.format_patch.check_no_path_traversal"):
                    with patch("pathlib.Path.mkdir"):
                        mock_sub = Mock()
                        mock_sub.patch = ["some.patch"]
                        mock_sub.on_disk_version.side_effect = RuntimeError("oops")
                        mock_create.return_value = mock_sub

                        args = argparse.Namespace(projects=[], output_directory=".")
                        with pytest.raises(RuntimeError):
                            format_patch(args)


# ============================
# UpdatePatch command
# ============================


def test_update_patch_raises_for_novcs():
    """UpdatePatch raises RuntimeError immediately for NoVcsSuperProject."""
    update_patch = UpdatePatch()
    superproject = Mock(spec=NoVcsSuperProject)
    superproject.root_directory = Path("/tmp")
    superproject.manifest = mock_manifest([])

    with patch(
        "dfetch.commands.update_patch.create_super_project", return_value=superproject
    ):
        args = argparse.Namespace(projects=[])
        with pytest.raises(RuntimeError, match="not under version control"):
            update_patch(args)


def test_update_patch_no_patch_logs_warning():
    """UpdatePatch logs a warning when the project has no patch."""
    from dfetch.project.gitsuperproject import GitSuperProject

    update_patch = UpdatePatch()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = Mock(spec=GitSuperProject)
    superproject.manifest = manifest
    superproject.root_directory = Path("/tmp")

    with patch(
        "dfetch.commands.update_patch.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.update_patch.in_directory"):
            with patch(
                "dfetch.commands.update_patch.dfetch.project.create_sub_project"
            ) as mock_create:
                with patch("dfetch.commands.update_patch.logger") as mock_logger:
                    mock_sub = Mock()
                    mock_sub.patch = []  # no patch
                    mock_create.return_value = mock_sub

                    args = argparse.Namespace(projects=[])
                    update_patch(args)

                    mock_logger.print_warning_line.assert_called_once()
                    call_args = mock_logger.print_warning_line.call_args[0]
                    assert "no patch file" in call_args[1]


def test_update_patch_no_on_disk_version_logs_warning():
    """UpdatePatch logs a warning when the project was never fetched."""
    from dfetch.project.gitsuperproject import GitSuperProject

    update_patch = UpdatePatch()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = Mock(spec=GitSuperProject)
    superproject.manifest = manifest
    superproject.root_directory = Path("/tmp")

    with patch(
        "dfetch.commands.update_patch.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.update_patch.in_directory"):
            with patch(
                "dfetch.commands.update_patch.dfetch.project.create_sub_project"
            ) as mock_create:
                with patch("dfetch.commands.update_patch.logger") as mock_logger:
                    mock_sub = Mock()
                    mock_sub.patch = ["my.patch"]
                    mock_sub.on_disk_version.return_value = None
                    mock_create.return_value = mock_sub

                    args = argparse.Namespace(projects=[])
                    update_patch(args)

                    mock_logger.print_warning_line.assert_called_once()
                    call_args = mock_logger.print_warning_line.call_args[0]
                    assert "never fetched" in call_args[1]


def test_update_patch_uncommitted_changes_logs_warning():
    """UpdatePatch logs a warning when there are uncommitted local changes."""
    from dfetch.project.gitsuperproject import GitSuperProject
    from dfetch.project.metadata import Metadata

    update_patch = UpdatePatch()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = Mock(spec=GitSuperProject)
    superproject.manifest = manifest
    superproject.root_directory = Path("/tmp")
    superproject.has_local_changes_in_dir.return_value = True

    with patch(
        "dfetch.commands.update_patch.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.update_patch.in_directory"):
            with patch(
                "dfetch.commands.update_patch.dfetch.project.create_sub_project"
            ) as mock_create:
                with patch("dfetch.commands.update_patch.logger") as mock_logger:
                    mock_sub = Mock()
                    mock_sub.patch = ["my.patch"]
                    mock_sub.on_disk_version.return_value = Mock()
                    mock_sub.local_path = "/tmp/myproj"
                    mock_create.return_value = mock_sub

                    args = argparse.Namespace(projects=[])
                    update_patch(args)

                    mock_logger.print_warning_line.assert_called_once()
                    call_args = mock_logger.print_warning_line.call_args[0]
                    assert "Uncommitted changes" in call_args[1]


def test_update_patch_runtime_error_raises_at_end():
    """UpdatePatch raises RuntimeError at end when any project processing fails."""
    from dfetch.project.gitsuperproject import GitSuperProject

    update_patch = UpdatePatch()
    manifest = mock_manifest([{"name": "myproj"}])
    superproject = Mock(spec=GitSuperProject)
    superproject.manifest = manifest
    superproject.root_directory = Path("/tmp")

    with patch(
        "dfetch.commands.update_patch.create_super_project", return_value=superproject
    ):
        with patch("dfetch.commands.update_patch.in_directory"):
            with patch(
                "dfetch.commands.update_patch.dfetch.project.create_sub_project"
            ) as mock_create:
                mock_sub = Mock()
                mock_sub.patch = ["my.patch"]
                mock_sub.on_disk_version.side_effect = RuntimeError("disk error")
                mock_create.return_value = mock_sub

                args = argparse.Namespace(projects=[])
                with pytest.raises(RuntimeError):
                    update_patch(args)


def test_update_patch_update_patch_with_text_writes_file():
    """_update_patch writes patch text to file when text is non-empty."""
    from dfetch.commands.update_patch import UpdatePatch

    up = UpdatePatch()

    with patch("dfetch.commands.update_patch.check_no_path_traversal"):
        with patch("pathlib.Path.write_text") as mock_write:
            with patch("dfetch.commands.update_patch.logger") as mock_logger:
                result = up._update_patch(
                    "/tmp/my.patch", Path("/tmp"), "myproj", "some patch text"
                )
                mock_write.assert_called_once_with("some patch text", encoding="UTF-8")
                mock_logger.print_info_line.assert_called_once()
                assert result is not None


def test_update_patch_update_patch_no_text_logs_info():
    """_update_patch logs info and returns path when patch text is empty."""
    from dfetch.commands.update_patch import UpdatePatch

    up = UpdatePatch()

    with patch("dfetch.commands.update_patch.check_no_path_traversal"):
        with patch("pathlib.Path.write_text") as mock_write:
            with patch("dfetch.commands.update_patch.logger") as mock_logger:
                result = up._update_patch("/tmp/my.patch", Path("/tmp"), "myproj", "")
                mock_write.assert_not_called()
                mock_logger.print_info_line.assert_called_once()
                assert "unchanged" in mock_logger.print_info_line.call_args[0][1]
                assert result is not None


def test_update_patch_update_patch_outside_root_logs_warning():
    """_update_patch logs a warning and returns None when patch is outside root."""
    from dfetch.commands.update_patch import UpdatePatch

    up = UpdatePatch()

    with patch(
        "dfetch.commands.update_patch.check_no_path_traversal",
        side_effect=RuntimeError("path traversal"),
    ):
        with patch("dfetch.commands.update_patch.logger") as mock_logger:
            result = up._update_patch(
                "/tmp/my.patch", Path("/other/root"), "myproj", "some text"
            )
            mock_logger.print_warning_line.assert_called_once()
            assert result is None

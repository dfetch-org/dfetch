"""*Dfetch* can filter files in the repo.

It can either accept no input to list all files. A list of files can be piped in (such as through ``find``)
or it can be used as a wrapper around a certain tool to block or allow files under control by dfetch.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import dfetch.commands.command
import dfetch.log
import dfetch.manifest.manifest
from dfetch.log import get_logger
from dfetch.util.cmdline import run_on_cmdline_uncaptured
from dfetch.util.util import in_directory

logger = get_logger(__name__)


class Filter(dfetch.commands.command.Command):
    """Filter files based on flags and pass on any command.

    Based on the provided arguments filter files, and call the given arguments or print them out if no command given.
    """

    SILENT = True

    @staticmethod
    def create_menu(subparsers: dfetch.commands.command.SubparserActionType) -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Filter)
        parser.add_argument(
            "--in-manifest",
            "-i",
            action="store_true",
            default=False,
            help="Keep files that came here through the manifest.",
        )

        parser.add_argument(
            "cmd",
            metavar="<cmd>",
            type=str,
            nargs="?",
            help="Command to call",
        )

        parser.add_argument(
            "args",
            metavar="<args>",
            type=str,
            nargs="*",
            help="Arguments to pass to the command",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the filter."""
        if not args.verbose:
            dfetch.log.set_level("ERROR")
        manifest = dfetch.manifest.manifest.get_manifest()

        pwd = Path.cwd()
        topdir = Path(manifest.path).parent
        with in_directory(topdir):

            project_paths = {
                Path(project.destination).resolve() for project in manifest.projects
            }

            input_list = self._determine_input_list(args)
            block_inside, block_outside = self._filter_files(
                pwd, topdir, project_paths, input_list
            )

        blocklist = block_outside if args.in_manifest else block_inside

        filtered_args = [arg for arg in input_list if arg not in blocklist]

        if args.cmd:
            run_on_cmdline_uncaptured(logger, [args.cmd] + filtered_args)
        else:
            print(os.linesep.join(filtered_args))

    def _determine_input_list(self, args: argparse.Namespace) -> list[str]:
        """Determine list of inputs to process."""
        input_list: list[str] = list(str(arg) for arg in args.args)
        if not sys.stdin.isatty():
            input_list += list(str(arg).strip() for arg in sys.stdin.readlines())

        # If no input from stdin or args loop over all files
        if not input_list:
            input_list = list(
                str(file) for file in Path(".").rglob("*") if file.is_file()
            )

        return input_list

    def _filter_files(
        self, pwd: Path, topdir: Path, project_paths: set[Path], input_list: list[str]
    ) -> tuple[list[str], list[str]]:
        """Filter files in input_set in files in one of the project_paths or not."""
        block_inside: list[str] = []
        block_outside: list[str] = []

        for path_or_arg in input_list:
            arg_abs_path = Path(pwd / path_or_arg.strip()).resolve()
            if not arg_abs_path.exists():
                logger.print_info_line(path_or_arg.strip(), "not a file / dir")
                continue
            try:
                arg_abs_path.relative_to(topdir)
            except ValueError:
                logger.print_info_line(path_or_arg.strip(), "outside project")
                block_inside.append(path_or_arg)
                block_outside.append(path_or_arg)
                continue

            containing_dir = self._file_in_project(arg_abs_path, project_paths)

            if containing_dir:
                block_inside.append(path_or_arg)
                logger.print_info_line(
                    path_or_arg.strip(), f"inside project ({containing_dir})"
                )
            else:
                block_outside.append(path_or_arg)
                logger.print_info_line(path_or_arg.strip(), "not inside any project")

        return block_inside, block_outside

    def _file_in_project(self, file: Path, project_paths: set[Path]) -> Optional[Path]:
        """Check if a specific file is somewhere in one of the project paths."""
        for project_path in project_paths:
            try:
                file.relative_to(project_path)
                return project_path
            except ValueError:
                continue
        return None

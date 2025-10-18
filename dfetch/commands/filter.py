"""*Dfetch* can filter files in the repo.

It can either accept no input to list all files. A list of files can be piped in (such as through ``find``)
or it can be used as a wrapper around a certain tool to block or allow files under control by dfetch.
"""

import argparse
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import dfetch.commands.command
import dfetch.log
import dfetch.manifest.manifest
from dfetch.log import get_logger
from dfetch.util.cmdline import run_on_cmdline_uncaptured
from dfetch.util.util import in_directory

logger = get_logger(__name__)


class FilterType(Enum):
    """Types of filtering."""

    BLOCK_ONLY_PATH_TRAVERSAL = 0
    BLOCK_IF_INSIDE = 1
    BLOCK_IF_OUTSIDE = 2


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
            "--dfetched",
            "-D",
            action="store_true",
            default=True,
            help="Keep files that came here by dfetching them.",
        )

        parser.add_argument(
            "--not-dfetched",
            "-N",
            action="store_true",
            default=False,
            help="Keep files that did not came here by dfetching them.",
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

        argument_list = self._get_arguments(args)

        manifest = dfetch.manifest.manifest.get_manifest()
        topdir = Path(manifest.path).parent

        resolved_args = self._resolve_args(argument_list, topdir)

        with in_directory(topdir):
            abs_project_paths = {
                Path(project.destination).resolve() for project in manifest.projects
            }

        if args.dfetched and not args.not_dfetched:
            block_type = FilterType.BLOCK_IF_OUTSIDE
        elif args.not_dfetched:
            block_type = FilterType.BLOCK_IF_INSIDE
        else:
            block_type = FilterType.BLOCK_ONLY_PATH_TRAVERSAL

        filtered_args = self._filter_args(
            topdir, resolved_args, abs_project_paths, block_type
        )

        if args.cmd:
            run_on_cmdline_uncaptured(logger, [args.cmd] + filtered_args)
        else:
            print(os.linesep.join(filtered_args))

    def _filter_args(
        self,
        topdir: Path,
        resolved_args: dict[str, Optional[Path]],
        abs_project_paths: set[Path],
        block: FilterType,
    ) -> list[str]:
        blocklist = self._filter_files(
            topdir,
            abs_project_paths,
            {path for path in resolved_args.values() if path},
            block,
        )

        filtered_args = [
            arg for arg in resolved_args.keys() if resolved_args[arg] not in blocklist
        ]

        return filtered_args

    def _resolve_args(
        self, argument_list: list[str], topdir: Path
    ) -> dict[str, Optional[Path]]:
        resolved_args: dict[str, Optional[Path]] = {}
        if argument_list:
            for argument in argument_list:
                path_obj = Path(argument.strip())
                resolved_args[argument] = (
                    path_obj.resolve() if path_obj.exists() else None
                )
        else:
            if not argument_list:
                resolved_args = {
                    str(file): file.resolve()
                    for file in topdir.rglob("*")
                    if ".git" not in file.parts
                }

        return resolved_args

    def _get_arguments(self, args: argparse.Namespace) -> list[str]:
        argument_list: list[str] = list(str(arg) for arg in args.args)
        if not sys.stdin.isatty():
            argument_list.extend(
                non_empty_line for line in sys.stdin if (non_empty_line := line.strip())
            )

        return argument_list

    def _filter_files(
        self,
        topdir: Path,
        paths: set[Path],
        input_paths: set[Path],
        block: FilterType = FilterType.BLOCK_IF_OUTSIDE,
    ) -> list[Path]:
        """Filter files in input_set in files in one of the paths or not."""
        blocklist: list[Path] = []

        for abs_path in input_paths:
            try:
                abs_path.relative_to(topdir)
            except ValueError:
                logger.print_info_line(str(abs_path), "outside project")
                blocklist.append(abs_path)
                continue

            if block == FilterType.BLOCK_ONLY_PATH_TRAVERSAL:
                continue

            containing_dir = self._is_file_contained_in_any_path(abs_path, paths)

            if containing_dir:
                logger.print_info_line(
                    str(abs_path), f"inside project ({containing_dir})"
                )
                if block == FilterType.BLOCK_IF_INSIDE:
                    blocklist.append(abs_path)
            else:
                logger.print_info_line(str(abs_path), "not inside any project")
                if block == FilterType.BLOCK_IF_OUTSIDE:
                    blocklist.append(abs_path)

        return blocklist

    def _is_file_contained_in_any_path(
        self, file: Path, paths: set[Path]
    ) -> Optional[Path]:
        """Check if a specific file is somewhere in one of the paths."""
        for path in paths:
            try:
                file.relative_to(path)
                return path
            except ValueError:
                continue
        return None

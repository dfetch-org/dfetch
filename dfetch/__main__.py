"""Find the complete documentation online.

https://dfetch.rtfd.org
"""

import argparse
import sys
from collections.abc import Sequence

from rich.console import Console

import dfetch.commands.add
import dfetch.commands.check
import dfetch.commands.diff
import dfetch.commands.environment
import dfetch.commands.format_patch
import dfetch.commands.freeze
import dfetch.commands.import_
import dfetch.commands.init
import dfetch.commands.report
import dfetch.commands.update
import dfetch.commands.update_patch
import dfetch.commands.validate
import dfetch.log
import dfetch.util.cmdline
from dfetch.log import DLogger


class DfetchFatalException(Exception):
    """Exception thrown when dfetch did not run successfully."""


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter, epilog=__doc__
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Increase verbosity"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    parser.set_defaults(func=_help)
    subparsers = parser.add_subparsers(help="commands")

    dfetch.commands.add.Add.create_menu(subparsers)
    dfetch.commands.check.Check.create_menu(subparsers)
    dfetch.commands.diff.Diff.create_menu(subparsers)
    dfetch.commands.environment.Environment.create_menu(subparsers)
    dfetch.commands.format_patch.FormatPatch.create_menu(subparsers)
    dfetch.commands.freeze.Freeze.create_menu(subparsers)
    dfetch.commands.import_.Import.create_menu(subparsers)
    dfetch.commands.init.Init.create_menu(subparsers)
    dfetch.commands.report.Report.create_menu(subparsers)
    dfetch.commands.update.Update.create_menu(subparsers)
    dfetch.commands.update_patch.UpdatePatch.create_menu(subparsers)
    dfetch.commands.validate.Validate.create_menu(subparsers)

    return parser


def _help(_: argparse.Namespace) -> None:
    """Show help if no subcommand was selected."""
    parser = create_parser()
    parser.print_help()


def run(argv: Sequence[str], console: Console | None = None) -> None:
    """Start dfetch."""
    args = create_parser().parse_args(argv)

    console = console or dfetch.log.make_console(no_color=args.no_color)
    logger: DLogger = dfetch.log.setup_root(__name__, console=console)

    logger.print_title()

    if args.verbose:
        dfetch.log.increase_verbosity()

    try:
        args.func(args)
    except (RuntimeError, TypeError) as exc:
        for msg in exc.args:
            logger.error(msg, stack_info=False)
        raise DfetchFatalException from exc
    except dfetch.util.cmdline.SubprocessCommandError as exc:
        logger.error(exc.message)
        raise DfetchFatalException from exc


def main() -> None:
    """Start dfetch and let it collect arguments from the command-line."""
    try:
        run(sys.argv[1:])
    except DfetchFatalException:
        sys.exit(1)


if __name__ == "__main__":
    main()

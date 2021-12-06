"""Find the complete documentation online.

https://dfetch.rtfd.org
"""

import argparse
import sys
from typing import Sequence

import dfetch.commands.check
import dfetch.commands.diff
import dfetch.commands.environment
import dfetch.commands.freeze
import dfetch.commands.import_
import dfetch.commands.init
import dfetch.commands.report
import dfetch.commands.update
import dfetch.commands.validate
import dfetch.log
import dfetch.util.cmdline

logger = dfetch.log.setup_root(__name__)


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
    parser.set_defaults(func=_help)
    subparsers = parser.add_subparsers(help="commands")

    dfetch.commands.check.Check.create_menu(subparsers)
    dfetch.commands.diff.Diff.create_menu(subparsers)
    dfetch.commands.environment.Environment.create_menu(subparsers)
    dfetch.commands.freeze.Freeze.create_menu(subparsers)
    dfetch.commands.import_.Import.create_menu(subparsers)
    dfetch.commands.init.Init.create_menu(subparsers)
    dfetch.commands.report.Report.create_menu(subparsers)
    dfetch.commands.update.Update.create_menu(subparsers)
    dfetch.commands.validate.Validate.create_menu(subparsers)

    return parser


def _help(args: argparse.Namespace) -> None:
    """Show the help."""
    raise RuntimeError("Select a function")


def run(argv: Sequence[str]) -> None:
    """Start dfetch."""
    logger.print_title()
    args = create_parser().parse_args(argv)

    if args.verbose:
        dfetch.log.increase_verbosity()

    try:
        args.func(args)
    except RuntimeError as exc:
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

"""Main entry point of command-line tool.

Created on 28/04/2020
@author: Ben Spoor
"""

import argparse
import sys

import dfetch.commands.check
import dfetch.commands.environment
import dfetch.commands.import_
import dfetch.commands.init
import dfetch.commands.update
import dfetch.commands.validate
import dfetch.log
import dfetch.util.cmdline

logger = dfetch.log.setup_root(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Increase verbosity"
    )
    parser.set_defaults(func=_help)
    subparsers = parser.add_subparsers(help="commands")

    dfetch.commands.init.Init.create_menu(subparsers)
    dfetch.commands.import_.Import.create_menu(subparsers)
    dfetch.commands.check.Check.create_menu(subparsers)
    dfetch.commands.environment.Environment.create_menu(subparsers)
    dfetch.commands.update.Update.create_menu(subparsers)
    dfetch.commands.validate.Validate.create_menu(subparsers)

    return parser


def _help(args: argparse.Namespace) -> None:
    """Show the help."""
    raise RuntimeError("Select a function")


def main() -> None:
    """Start dfetch."""
    logger.print_title()
    args = create_parser().parse_args()

    if args.verbose:
        dfetch.log.increase_verbosity()

    try:
        args.func(args)
    except RuntimeError as exc:
        for msg in exc.args:
            logger.error(msg, stack_info=False)
        sys.exit(1)
    except dfetch.util.cmdline.SubprocessCommandError as exc:
        logger.error(exc.message)
        sys.exit(1)


if __name__ == "__main__":
    main()

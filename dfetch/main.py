"""
Created on 28/04/2020
@author: Ben Spoor
"""

import argparse
import sys

from colorama import Fore

from dfetch import __version__
import dfetch.commands.init
import dfetch.commands.update
import dfetch.commands.validate
import dfetch.util.cmdline
import dfetch.log

logger = dfetch.log.setup_root(__name__)


def create_parser() -> argparse.ArgumentParser:
    """ Create the main argument parser """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.set_defaults(func=_help)
    subparsers = parser.add_subparsers(help="commands")

    dfetch.commands.init.Init.create_menu(subparsers)
    dfetch.commands.update.Update.create_menu(subparsers)
    dfetch.commands.validate.Validate.create_menu(subparsers)

    return parser


def _help(args: argparse.Namespace) -> None:
    """ """
    raise RuntimeError("Select a function")


def main() -> None:
    """ Start dfetch """
    logger.info(f"{Fore.BLUE}Dfetch ({__version__})")
    args = create_parser().parse_args()

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

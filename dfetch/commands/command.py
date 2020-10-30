"""
A generic command
"""

import argparse
from typing import Type, TypeVar


class Command:
    """An abstract command that dfetch can perform

    Each commond must implemened :ref:`create_menu` and :ref:`__call__`
    """

    CHILD_TYPE = TypeVar("CHILD_TYPE", bound="Command")

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """ Add a subparser to the given parser """
        raise NotImplementedError("Should be implemented")

    def __call__(self, args: argparse.Namespace) -> None:
        raise NotImplementedError("Should be implemented")

    @staticmethod
    def parser(
        subparsers: "argparse._SubParsersAction", command: Type["Command.CHILD_TYPE"]
    ) -> "argparse.ArgumentParser":
        """ Create a parser """

        if not command.__doc__:
            raise NotImplementedError("Must add docstring to class")
        help_str, epilog = command.__doc__.split("\n", 1)

        parser = subparsers.add_parser(
            command.__name__.lower(),
            description=help_str,
            help=help_str,
            epilog=epilog,
        )

        parser.set_defaults(func=command())
        return parser

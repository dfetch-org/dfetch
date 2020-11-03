"""A generic command."""

import argparse
from abc import ABC, abstractmethod
from typing import Type, TypeVar


class Command(ABC):
    """An abstract command that dfetch can perform.

    When adding a new command to dfetch this class should be sub-classed.
    That subclass should implement:

    - ``create_menu`` which should add an appropriate subparser.
        Likely calling parser is enough.
    - ``__call__`` which will be called when the user selects the command.
    """

    CHILD_TYPE = TypeVar("CHILD_TYPE", bound="Command")  # noqa

    @staticmethod
    @abstractmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add a sub-parser to the given parser.

        Args:
            subparsers (argparse._SubParsersAction): subparser that the parser should be added to.

        This method must be implemented by a subclass. It is called when the menu structure is built.
        """

    @abstractmethod
    def __call__(self, args: argparse.Namespace) -> None:
        """Perform the command.

        Args:
            args (argparse.Namespace): arguments as provided by the user.

        Raises:
            NotImplementedError: This is an abstract method that should be implemented by a subclass.
        """

    @staticmethod
    def parser(
        subparsers: "argparse._SubParsersAction", command: Type["Command.CHILD_TYPE"]
    ) -> "argparse.ArgumentParser":
        """Generate the parser.

        The name of the class will be used as command. The class docstring will be split into
        the help text, description and epilog.

        Args:
            subparsers: The subparser to add the command to.
            command: The command class that should be instantiated and called when this command is called.

        Raises:
            NotImplementedError: If the child class doesn't have a docstring.

        Returns:
            Command: A argparse.ArgumentParser that can be used to add arguments.
        """
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

"""Custom Pygments style matching the dfetch website brand palette."""

import sys
import types
from typing import MutableMapping, cast

import pygments.styles
from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Token,
)


class DfetchStyle(Style):  # pylint: disable=too-few-public-methods
    """Brand-matched Pygments style — mirrors the website palette."""

    background_color = "#fef8f0"  # --bg-tint
    default_style = ""
    styles = {
        Token: "#1c1917",  # --text
        Comment: "italic #78716c",  # --text-muted
        Comment.Preproc: "noitalic #a0510a",  # --primary-dark
        Keyword: "bold #c2620a",  # --primary
        Keyword.Pseudo: "nobold #c2620a",
        Operator: "#a0510a",  # --primary-dark
        Operator.Word: "bold #c2620a",
        String: "#4a7a62",  # --dxt-reference (sage)
        String.Doc: "italic #4a7a62",
        Number: "#7a5a9a",  # --dxt-explanation (purple)
        Name.Builtin: "#4e7fa0",  # --accent
        Name.Builtin.Pseudo: "#4e7fa0",
        Name.Class: "bold #4e7fa0",
        Name.Function: "#3a6682",  # --accent-dark
        Name.Exception: "bold #c0544a",  # --dferror
        Name.Decorator: "#78716c",  # --text-muted
        Name.Tag: "bold #c2620a",  # --primary
        Name.Attribute: "#4e7fa0",  # --accent
        Generic.Heading: "bold #1c1917",
        Generic.Subheading: "bold #78716c",
        Generic.Deleted: "#c0544a",  # --dferror
        Generic.Inserted: "#4a7a62",  # sage green
        Generic.Error: "#c0544a",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Generic.Prompt: "bold #c2620a",  # --primary
        Generic.Output: "#78716c",  # --text-muted
        Generic.Traceback: "#4e7fa0",  # --accent
        Error: "border:#c0544a",
    }


def register() -> None:
    """Inject the style into Pygments so it can be looked up by name."""
    mod = types.ModuleType("pygments.styles.dfetch")
    mod.DfetchStyle = DfetchStyle  # type: ignore[attr-defined]
    sys.modules["pygments.styles.dfetch"] = mod
    cast(MutableMapping[str, str], pygments.styles.STYLE_MAP)[
        "dfetch"
    ] = "dfetch::DfetchStyle"

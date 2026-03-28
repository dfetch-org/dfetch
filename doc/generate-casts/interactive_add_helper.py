#!/usr/bin/env python3
"""Drive ``dfetch add -i`` with simulated typing for asciinema recordings.

Usage::

    python3 interactive-add-helper.py <remote-url>

Every Rich ``Prompt.ask`` / ``Confirm.ask`` call is intercepted:

1. The prompt markup is rendered to the terminal exactly as dfetch would.
2. After a short "thinking" pause each answer character is written to stdout
   one at a time, mimicking natural typing speed.
3. The answer is returned to dfetch as if the user had pressed Enter.

``is_tty`` is forced to ``False`` so that dfetch uses the text-based
fallbacks (numbered version list, plain src/ignore prompts) rather than
the raw-terminal tree browser – the text fallback looks better on a cast.

Answers
-------
``None`` in a prompt-answer slot means "accept the default" – the default
value is typed out so the viewer can read what was chosen.  An explicit
string overrides the default.
"""

from __future__ import annotations

import sys
import time
from collections import deque
from unittest.mock import patch

from rich.console import Console

# ---------------------------------------------------------------------------
# Wizard answers – customise these to change what the demo shows
# ---------------------------------------------------------------------------
_PROMPT_ANSWERS: deque[str | None] = deque(
    [
        None,  # Name          – accept the default (derived from URL)
        "ext/cpputest",  # Destination   – show the common ext/ convention
        None,  # Version       – accept the default branch
        None,  # Source path   – press Enter to fetch the whole repo
        None,  # Ignore paths  – press Enter to skip
    ]
)
_CONFIRM_ANSWERS: deque[bool] = deque(
    [
        True,  # "Add project to manifest?" → yes
        False,  # "Run 'dfetch update' now?" → no
    ]
)

# ---------------------------------------------------------------------------
# Timing (seconds) – tweak for faster/slower recording
# ---------------------------------------------------------------------------
_PRE_DELAY = 0.55  # pause before starting to type (user "thinking")
_CHAR_DELAY = 0.06  # delay between consecutive characters

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
_console = Console(force_terminal=True)


def _type_out(text: str) -> None:
    """Write *text* to stdout one character at a time, then a newline."""
    time.sleep(_PRE_DELAY)
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(_CHAR_DELAY)
    sys.stdout.write("\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Prompt replacements
# ---------------------------------------------------------------------------


def _fake_prompt_ask(prompt_markup: str, *, default: str = "", **_kw: object) -> str:
    """Render the Rich-markup prompt, then simulate typing the next answer.

    ``None`` in the queue means "accept the default" – the default is
    typed out (visible to the viewer) rather than silently accepted.
    """
    suffix = f" [{default}]" if default else ""
    _console.print(f"{prompt_markup}{suffix}: ", end="")

    raw = _PROMPT_ANSWERS.popleft() if _PROMPT_ANSWERS else None
    answer = raw if raw is not None else default
    _type_out(answer)
    return answer


def _fake_confirm_ask(
    prompt_markup: str, *, default: bool = True, **_kw: object
) -> bool:
    """Render the confirm prompt, then simulate typing y or n."""
    yn_hint = "y" if default else "n"
    _console.print(f"{prompt_markup} [y/n] ({yn_hint}): ", end="")

    val = _CONFIRM_ANSWERS.popleft() if _CONFIRM_ANSWERS else default
    _type_out("y" if val else "n")
    return val


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: interactive-add-helper.py <remote-url>")

    url = sys.argv[1]

    # Force text-mode prompts so dfetch uses the numbered list + plain prompts
    # instead of the raw-TTY tree browser.
    import dfetch.terminal.keys as _keys

    _keys.is_tty = lambda: False  # type: ignore[assignment]

    with patch("rich.prompt.Prompt.ask", side_effect=_fake_prompt_ask):
        with patch("rich.prompt.Confirm.ask", side_effect=_fake_confirm_ask):
            from dfetch.__main__ import run

            run(["add", "--interactive", url], _console)

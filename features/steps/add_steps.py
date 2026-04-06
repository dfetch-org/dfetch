"""Steps for the 'dfetch add' feature tests."""

# pylint: disable=missing-function-docstring, import-error, not-callable
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false

from collections import deque
from unittest.mock import patch

from behave import then, when  # pylint: disable=no-name-in-module

from features.steps.generic_steps import call_command, remote_server_path
from features.steps.manifest_steps import apply_manifest_substitutions


def _run_interactive_add(context, cmd: list[str]) -> None:
    """Run an interactive add command, driving prompts from ``context.table``."""
    # Parse the answer table into three buckets:
    #   • "Add project to manifest?" → add_confirm (bool)
    #   • "Run" + "update" in prompt  → update_confirm (bool, default False)
    #   • anything else               → Prompt.ask answers (in order)
    add_confirm = True
    update_confirm = False
    prompt_answers: deque[str] = deque()

    for row in context.table:
        question = row["Question"]
        answer = row["Answer"]
        if "Add project to manifest" in question:
            add_confirm = answer.lower() not in ("n", "no", "false")
        elif "update" in question.lower() and "run" in question.lower():
            update_confirm = answer.lower() not in ("n", "no", "false")
        else:
            prompt_answers.append(answer)

    # Two sequential Confirm calls: first "add?", then (if added) "update?".
    # We use an iterator so each call consumes the next value.
    _confirm_values = iter([add_confirm, update_confirm])

    def _auto_confirm(_prompt: str, **kwargs) -> bool:
        try:
            return next(_confirm_values)
        except StopIteration:
            return bool(kwargs.get("default", False))

    def _auto_prompt(_prompt: str, **kwargs) -> str:  # type: ignore[return]
        """Return the next pre-defined answer, ignoring the actual prompt text."""
        if prompt_answers:
            return prompt_answers.popleft()
        return str(kwargs.get("default", ""))

    with patch("dfetch.commands.add.Prompt.ask", side_effect=_auto_prompt):
        with patch("dfetch.commands.add.Confirm.ask", side_effect=_auto_confirm):
            call_command(context, cmd)


@when('I run "dfetch {add_args}" with inputs')
def step_interactive_add(context, add_args):
    resolved = add_args.replace("some-remote-server", remote_server_path(context))
    _run_interactive_add(context, resolved.split())


@then("the manifest '{name}' contains entry")
def step_manifest_contains_entry(context, name):
    expected = apply_manifest_substitutions(context, context.text)
    with open(name, "r", encoding="utf-8") as fh:
        actual = fh.read()

    # Check that every line of the expected snippet is present somewhere in
    # the manifest (order-insensitive substring check per line).
    missing = []
    for line in expected.splitlines():
        stripped = line.strip()
        if stripped and stripped not in actual:
            missing.append(line)

    if missing:
        print("Actual manifest:")
        print(actual)
        assert not missing, "Expected lines not found in manifest:\n" + "\n".join(
            missing
        )


@then('the command fails with "{message}"')
def step_command_fails_with(context, message):
    assert context.cmd_returncode != 0, "Expected command to fail, but it succeeded"
    assert (
        message in context.cmd_output
    ), f"Expected error message '{message}' not found in output:\n{context.cmd_output}"


@then("the manifest '{name}' does not contain '{text}'")
def step_manifest_not_contain(_, name, text):
    with open(name, "r", encoding="utf-8") as fh:
        actual = fh.read()

    if text in actual:
        print("Actual manifest:")
        print(actual)
        assert False, f"Expected text '{text}' should not be in manifest"

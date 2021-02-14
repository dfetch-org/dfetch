"""Steps for features tests."""


from behave import given, then  # pylint: disable=no-name-in-module


@given("the manifest '{name}'")
@when("the manifest '{name}' is changed to")
def step_impl(context, name):
    with open(name, "w") as manifest:
        for line in context.text.splitlines():
            print(line, file=manifest)


@then("it should generate the manifest '{name}'")
def step_impl(context, name):
    """Check a manifest."""
    with open(name, "r") as manifest:

        for actual, expected in zip(
            context.text.splitlines(True), manifest.readlines()
        ):

            assert (
                actual.strip() == expected.strip()
            ), f"Actual {actual.strip()} != Expected {expected.strip()}"

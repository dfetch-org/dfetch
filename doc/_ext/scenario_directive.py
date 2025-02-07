from docutils import nodes
from docutils.parsers.rst import Directive


class ScenarioIncludeDirective(Directive):
    """Custom directive to dynamically include scenarios from a Gherkin feature file."""

    required_arguments = 1  # Only the feature file is required
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "scenario": str,
    }

    def run(self):
        feature_file = self.arguments[0].strip()
        scenario_titles = [
            title.strip()
            for title in self.options.get("scenario", "").splitlines()
            if title.strip()
        ]

        if not scenario_titles:
            raise self.error("At least one :scenario: must be provided.")

        container = nodes.section()

        for scenario_title in scenario_titles:
            directive_rst = f"""
.. details:: **Example**: {scenario_title}

    .. literalinclude:: {feature_file}
        :language: gherkin
        :caption: {feature_file}
        :start-after: Scenario: {scenario_title}
        :end-before: Scenario:
        :force:
        :dedent:
"""
            self.state.nested_parse(
                self.state_machine.input_lines.__class__(directive_rst.splitlines()),
                self.content_offset,
                container,
            )

        return container.children  # Return parsed nodes instead of raw text


def setup(app):
    app.add_directive("scenario-include", ScenarioIncludeDirective)

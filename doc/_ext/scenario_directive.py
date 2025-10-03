"""
This custom Sphinx directive dynamically includes scenarios from a Gherkin feature file.

1. Enable the directive in your Sphinx `conf.py`:

```python
   extensions = ["your_extension_folder.scenario_directive"]
```

Use it in an .rst file:

```rst
.. scenario-include:: path/to/feature_file.feature
   :scenario:
      Scenario Title 1
      Scenario Title 2
```

If `:scenario:` is omitted, all scenarios in the feature file will be included.
The directive automatically detects Scenario: and Scenario Outline: titles.

"""

import os
import re
from typing import Tuple

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList


class ScenarioIncludeDirective(Directive):
    """Custom directive to dynamically include scenarios from a Gherkin feature file."""

    required_arguments = 1  # Only the feature file is required
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "scenario": str,
    }

    def list_of_scenarios(self, feature_file_path: str) -> Tuple[str]:
        """Parse the list of scenarios from the feature file"""
        env = self.state.document.settings.env
        feature_path = os.path.abspath(os.path.join(env.app.srcdir, feature_file_path))
        if not os.path.exists(feature_path):
            raise self.error(f"Feature file not found: {feature_path}")

        with open(feature_path, encoding="utf-8") as f:
            scenarios = tuple(
                m[1]
                for m in re.findall(
                    r"^\s*(Scenario(?: Outline)?):\s*(.+)$", f.read(), re.MULTILINE
                )
            )
        return scenarios

    def run(self):
        """Generate the same literalinclude block for every scenario."""
        feature_file = self.arguments[0].strip()

        scenarios_available = self.list_of_scenarios(feature_file)

        scenario_titles = [
            title.strip()
            for title in self.options.get("scenario", "").splitlines()
            if title.strip()
        ] or scenarios_available

        container = nodes.section()

        for scenario_title in scenario_titles:
            end_before = (
                ":end-before: Scenario:"
                if scenario_title != scenarios_available[-1]
                else ""
            )

            directive_rst = f"""
.. details:: **Example**: {scenario_title}

    .. literalinclude:: {feature_file}
        :language: gherkin
        :caption: {feature_file}
        :force:
        :dedent:
        :start-after: Scenario: {scenario_title}
        {end_before}
"""
            viewlist = StringList()
            for i, line in enumerate(directive_rst.splitlines()):
                viewlist.append(line, source=f"<{self.name} directive>", offset=i)

            self.state.nested_parse(
                viewlist,
                self.content_offset,
                container,
            )

        return container.children


def setup(app):
    """Setup the directive."""
    app.add_directive("scenario-include", ScenarioIncludeDirective)

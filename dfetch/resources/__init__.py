"""Resources needed when dfetch is distributed."""

import importlib.resources

from dfetch import resources  # pylint: disable=import-self

SCHEMA_PATH = importlib.resources.path(resources, "schema.yaml")
TEMPLATE_PATH = importlib.resources.path(resources, "template.yaml")

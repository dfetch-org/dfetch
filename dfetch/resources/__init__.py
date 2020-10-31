"""Resources needed when dfetch is distributed."""

import importlib.resources as pkg_resources

from dfetch import resources  # pylint: disable=import-self

SCHEMA_PATH = pkg_resources.path(resources, "schema.yaml")
TEMPLATE_PATH = pkg_resources.path(resources, "template.yaml")

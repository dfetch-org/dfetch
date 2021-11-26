"""*Dfetch* can generate an SBoM, see https://cyclonedx.org/use-cases/ for more details."""

import argparse
import glob
import itertools
import os
import re

import infer_license
from cyclonedx.model import ExternalReference, ExternalReferenceType
from cyclonedx.model.bom import Bom, Tool
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.output import OutputFormat, get_instance

import dfetch.commands.command
import dfetch.manifest.manifest
import dfetch.util.util
from dfetch.log import get_logger
from dfetch.project.metadata import Metadata
from dfetch.manifest.project import ProjectEntry

logger = get_logger(__name__)

github_url = re.compile(r"github.com\/(?P<group>.+)\/(?P<repo>[^\s\.]+)[\.]?")

DFETCH_TOOL = Tool(vendor="dfetch-org", name="dfetch", version=dfetch.__version__)


class Sbom(dfetch.commands.command.Command):
    """Generate a SBoM containing information about the projects components.

    Generate a file for tracking licenses and vulnerabilities.
    """

    @staticmethod
    def create_menu(subparsers: "argparse._SubParsersAction") -> None:
        """Add the parser menu for this action."""
        parser = dfetch.commands.command.Command.parser(subparsers, Sbom)
        parser.add_argument(
            "-o",
            "--outfile",
            metavar="<filename>",
            type=str,
            default="SBoM.json",
            help="SBoM filename",
        )

    def __call__(self, args: argparse.Namespace) -> None:
        """Generate the SBoM."""
        manifest, path = dfetch.manifest.manifest.get_manifest()

        bom = Bom()
        bom.get_metadata().add_tool(DFETCH_TOOL)

        with dfetch.util.util.in_directory(os.path.dirname(path)):
            for project in manifest.projects:

                version = self._determine_version(project)

                match = github_url.search(project.remote_url)
                if match:
                    component = Component(
                        name=match.group("repo"),
                        version=version,
                        component_type=ComponentType.LIBRARY,
                        package_url_type="github",
                        namespace=match.group("group"),
                        subpath=project._src or None,
                    )
                else:
                    component = Component(
                        name=project.name,
                        version=version,
                        component_type=ComponentType.LIBRARY,
                        package_url_type="generic",
                        qualifiers=f"download_url={project.remote_url}",
                        subpath=project._src or None,
                    )
                    component.add_external_reference(
                        ExternalReference(
                            reference_type=ExternalReferenceType.VCS,
                            url=project.remote_url,
                        )
                    )

                component.set_license(self._determine_license(project))

                logger.debug(f"Added {project.name}")
                bom.add_component(component)

            output_format = (
                OutputFormat.XML if args.outfile.endswith(".xml") else OutputFormat.JSON
            )

            outputter = get_instance(bom=bom, output_format=output_format)

            outputter.output_to_file(args.outfile, allow_overwrite=True)
            logger.info(f"Created {args.outfile}")

    @staticmethod
    def _determine_license(project: ProjectEntry) -> str:
        """Try to determine license of fetched project."""
        with dfetch.util.util.in_directory(project.destination):
            for license_file in itertools.chain(
                glob.glob("LICENSE*"), glob.glob("COPYING*")
            ):
                logger.debug(f"Found license file {license_file} for {project.name}")
                license = infer_license.guess_file(license_file)
        return license.name

    @staticmethod
    def _determine_version(project: ProjectEntry) -> str:
        """Determine the fetched version."""
        try:
            metadata = Metadata.from_file(Metadata.from_project_entry(project).path)
            version = metadata.tag or metadata.revision or ""
        except FileNotFoundError:
            version = project.tag or project.revision or ""
        return version

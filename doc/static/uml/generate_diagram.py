import dataclasses
import glob
import os
import pathlib
import pprint
import re
from pathlib import Path
from typing import Sequence, Tuple

import_regex = re.compile(r"(import|from) dfetch\.(?P<relation>[\.\w]+)")
description_regex = re.compile(r"^\"{3}(?P<description>.*)")


@dataclasses.dataclass
class Relation:
    path: str


@dataclasses.dataclass
class Module:
    path: Tuple[str]
    name: str
    description: str
    relations: list


def find_relations(directory, blacklist=None):
    blacklist = blacklist or []
    relations = {}

    for python_file in glob.glob(f"{directory}/**/*.py", recursive=True):
        with open(python_file, "r", encoding="UTF-8") as source:
            path = Path(python_file).relative_to(directory)
            module_path = path.parent.parts

            if path.stem in blacklist:
                continue

            full_source_text = source.read()

            package = relations
            for part in module_path:
                try:
                    package = package[part]
                except KeyError:
                    package[part] = {}
                    package = package[part]

            package[path.stem] = Module(
                path=path.parent.parts,
                name=path.stem,
                description=description_regex.search(full_source_text)
                .group("description")
                .strip('"'),
                relations=[
                    Relation(relation.group("relation").split("."))
                    for relation in import_regex.finditer(full_source_text)
                ],
            )

    # pprint.pprint(relations)
    return relations


def generate_c3(relations, path: Sequence[str], blacklist=None):
    blacklist = blacklist or []

    C3_START_TEMPLATE = """
@startuml

!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

Person(user, "Developer")

System_Boundary(DFetch, "Dfetch") {
"""

    C3_END_TEMPLATE = """
}

Rel(user, contCommands, "Uses")

@enduml
    """
    indent = "    "
    outside_in = set()
    inside_out = set()
    related_containers = set()

    for container, modules in relations.items():
        if isinstance(modules, dict):
            if container != path[0]:
                for name, module in modules.items():
                    if isinstance(module, dict):
                        continue
                    for relation in module.relations:
                        if (
                            relation.path[0] == path[0]
                            and relation.path[0] not in blacklist
                        ):
                            outside_in.add(
                                f'{indent}Rel(cont{container}, comp{relation.path[-1]}, "Uses")'
                            )
                            related_containers.add(container)
            else:
                for name, module in modules.items():
                    if isinstance(module, dict):
                        continue
                    for relation in module.relations:
                        if (
                            relation.path[0] != path[0]
                            and relation.path[0] not in blacklist
                        ):
                            inside_out.add(
                                f'{indent}Rel(comp{module.name}, cont{relation.path[0]}, "Uses")'
                            )
                            related_containers.add(relation.path[0])

    print(C3_START_TEMPLATE)

    for container, modules in relations.items():
        if container == path[0]:
            print(f'{indent}Boundary(cont{container}, "Manifest") {{')

            for name, module in modules.items():
                description = (
                    "something" if isinstance(module, dict) else module.description
                )
                print(
                    f'{indent}{indent}Component(comp{name}, "{name}", "python", "{description}")'
                )

            print("")
            for name, module in modules.items():
                if isinstance(module, dict):
                    continue
                for relation in module.relations:
                    if relation.path[0] == container:
                        print(
                            f'{indent}{indent}Rel(comp{module.name}, comp{relation.path[1]}, "Uses")'
                        )

            print(f"{indent}}}")

        elif container in related_containers:
            print(
                f'{indent}Container(cont{container}, "{container}", "python", "Something.")'
            )
    print("")
    for relation in outside_in:
        print(relation)
    print("")

    for relation in inside_out:
        print(relation)
    print("")
    print(C3_END_TEMPLATE)


if __name__ == "__main__":
    blacklist = ("__init__", "__main__", "log", "util", "resources")
    script_path = pathlib.Path(os.path.realpath(__file__))
    module_path = script_path.parent.parent.parent.parent / "dfetch"
    relations = find_relations(module_path, blacklist)

    generate_c3(relations, ("vcs", "manifest"), blacklist)

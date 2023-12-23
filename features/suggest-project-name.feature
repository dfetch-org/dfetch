Feature: Suggest a project name

    Users sometimes mistype project names, this lead to blaming *DFetch* of wrong behavior.
    To help the user of *DFetch*, if a user specifies a  project name, that can't be found, suggest
    the closest.

    Background:
        Given the manifest 'dfetch.yaml' with the projects:
            | name                 |
            | project with space   |
            | project-with-l       |
            | Project-With-Capital |

    Scenario: Name with space
        When I run "dfetch check project with space"
        Then the output shows
            """
            Dfetch (0.8.0)
            Not all projects found! "project", "with", "space"
            This manifest contains: "project with space", "project-with-l", "Project-With-Capital"
            Did you mean: "project with space"?
            """

    Scenario: Name with one token different
        When I run "dfetch check project-with-1"
        Then the output shows
            """
            Dfetch (0.8.0)
            Not all projects found! "project-with-1"
            This manifest contains: "project with space", "project-with-l", "Project-With-Capital"
            Did you mean: "project-with-l"?
            """

    Scenario: Multiple wrong
        When I run "dfetch check project-with-1 project-with-space Project-With-Capital"
        Then the output shows
            """
            Dfetch (0.8.0)
            Not all projects found! "project-with-1", "project-with-space"
            This manifest contains: "project with space", "project-with-l", "Project-With-Capital"
            Did you mean: "project with space" and "project-with-l"?
            """

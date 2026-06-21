@environment
Feature: Display environment information

    dfetch environment shows information about the working environment,
    including the installed dfetch version and the versions of supported
    VCS tools found on PATH.

    Scenario: Environment information is shown
        When I run "dfetch environment"
        Then the output starts with:
            """
            Dfetch (0.14.2)
              dfetch              : 0.13.0
            """

    Scenario: A newer dfetch version is available
        Given dfetch "1.99.0" is available on GitHub
        When I run "dfetch environment"
        Then the output starts with:
            """
            Dfetch (0.14.2)
              dfetch              : 0.13.0
              dfetch 1.99.0 available — https://github.com/dfetch-org/dfetch/releases
            """

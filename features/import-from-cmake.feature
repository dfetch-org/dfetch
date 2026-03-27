Feature: Importing dependencies from CMake FetchContent and ExternalProject declarations

    Teams that manage dependencies via CMake's FetchContent or ExternalProject
    modules can migrate to Dfetch by running ``dfetch import --detect cmake``.
    Dfetch scans all ``CMakeLists.txt`` and ``*.cmake`` files in the repository
    and converts each ``FetchContent_Declare`` or ``ExternalProject_Add`` call
    into a manifest entry.

    Scenario: FetchContent_Declare with GIT_REPOSITORY is imported
        Given a git repository with the file "CMakeLists.txt"
            """
            cmake_minimum_required(VERSION 3.14)
            project(myproject)

            include(FetchContent)

            FetchContent_Declare(json
                GIT_REPOSITORY https://github.com/nlohmann/json.git
                GIT_TAG        v3.11.2
            )
            FetchContent_MakeAvailable(json)
            """
        When I run "dfetch import --detect cmake"
        Then it should generate the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
              - name: github-com-nlohmann
                url-base: https://github.com/nlohmann

              projects:
              - name: json
                tag: v3.11.2
                repo-path: json.git

            """

    Scenario: ExternalProject_Add with GIT_REPOSITORY is imported
        Given a git repository with the file "CMakeLists.txt"
            """
            cmake_minimum_required(VERSION 3.14)
            project(myproject)

            include(ExternalProject)

            ExternalProject_Add(googletest
                GIT_REPOSITORY https://github.com/google/googletest.git
                GIT_TAG        v1.14.0
            )
            """
        When I run "dfetch import --detect cmake"
        Then it should generate the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
              - name: github-com-google
                url-base: https://github.com/google

              projects:
              - name: googletest
                tag: v1.14.0
                repo-path: googletest.git

            """

    Scenario: CMakeLists.txt located in a subdirectory is scanned
        Given a git repository with the file "third_party/CMakeLists.txt"
            """
            include(FetchContent)

            FetchContent_Declare(spdlog
                GIT_REPOSITORY https://github.com/gabime/spdlog.git
                GIT_TAG        v1.13.0
            )
            """
        When I run "dfetch import --detect cmake"
        Then it should generate the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
              - name: github-com-gabime
                url-base: https://github.com/gabime

              projects:
              - name: spdlog
                tag: v1.13.0
                repo-path: spdlog.git

            """

    Scenario: Commented-out declarations are not imported
        Given a git repository with the file "CMakeLists.txt"
            """
            # FetchContent_Declare(ignored
            #     GIT_REPOSITORY https://github.com/example/ignored.git
            #     GIT_TAG v0.1
            # )

            FetchContent_Declare(real
                GIT_REPOSITORY https://github.com/nlohmann/json.git
                GIT_TAG        v3.11.2
            )
            """
        When I run "dfetch import --detect cmake"
        Then it should generate the manifest 'dfetch.yaml'
            """
            manifest:
              version: '0.0'

              remotes:
              - name: github-com-nlohmann
                url-base: https://github.com/nlohmann

              projects:
              - name: real
                tag: v3.11.2
                repo-path: json.git

            """

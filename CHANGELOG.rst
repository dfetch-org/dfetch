Release 0.11.0 (unreleased)
====================================

* Don't show animation when running in CI (#702)

Release 0.10.0 (released 2025-03-12)
====================================

* Support python 3.13
* Fix too strict overlapping path check (#684)
* Show complete URL of child manifests (#683)
* Show remote name when using default remote (#445)
* Select HEAD branch as default in git (#689)

Release 0.9.1 (released 2024-12-31)
===================================

* Fix pypi publishing

Release 0.9.0 (released 2024-12-30)
===================================

* Warn user if the remote does not exist (#185, #171)
* Report unavailable project version during check (#381)
* Don't look for update on random branch if only revision is provided in git (#393)
* Don't report update available if revision on disk matches revision in manifest for git (#393)
* Report the revision available in git if only revision is in git (#393)
* Add ``ignore`` list to project entries in the manifest (#571)

Release 0.8.0 (released 2023-12-23)
===================================

* Don't break if no suggestion found (#358)
* Drop python 3.6 support (#386)
* Fix checking project from svn branch (#383)
* Move all configuration into single ``pyproject.toml`` (#401)
* Also build for python 3.11, 3.12 in CI
* Add 3.11, 3.12 classifier to pyproject
* When importing non-std SVN external, identify ``src`` path

Release 0.7.0 (released 2022-06-22)
===================================

* Warn about local changes during check (#286)
* Add support for Gitlab-CI/Code Climate check reports (#18)
* Improve Sarif/github messages (#292)
* Update to CycloneDX spec 1.4 (#296)
* Never overwrite main project folder and manifest (#302)
* Add codespell and fix typo's (#303)
* Add warning to metadata file, not to change it (#170)
* Fix SBoM report (#337)
* Suggest a correct project name if not found (#320)
* Handle relative urls during dfetch import (#339)

Release 0.6.0 (released 2022-01-31)
===================================

* Pin dependencies
* Recommend child-projects instead of fetching (#242)
* Show spinner when fetching (#264)
* Don't allow path traversal for dst path
* Check for casing issues in ``dst:`` path during update (#256)
* Check for overlapping destinations of projects (#173)
* Handle invalid metadata file (#280)
* Update to CycloneDX spec 1.3 (#282)
* Make it possible to generate jenkins and sarif json report for check (#18)

Release 0.5.1 (released 2021-12-09)
===================================

* Pin dependencies

Release 0.5.0 (released 2021-12-09)
===================================

* Add diff command for svn projects (#24)
* Also add binary files as part of generated patch (#251)
* Create diff on working copy instead of current revision (#254)
* Deprecate ``dfetch list`` command for ``dfetch report`` command
* Add Software Bill-of-Materials (sBoM) export to ``dfetch report`` command (#154)
* Guess license for sbom export (#50)
* Match more licenses (#260)

Release 0.4.0 (released 2021-11-26)
===================================

* Add patch info to list command (#198)
* Don't break when there is a space in SVN dest path (#223)
* Fix unittest (#229)
* Allow using glob pattern for src key in manifest (#228)
* Add diff command (#24)
* Make dfetch work for python 3.6 (#32)

Release 0.3.0 (released 2021-07-19)
===================================

* Add list command (#20)
* Add warning when patch file isn't found (#191)
* Add project argument to check, update & list (#188)

Release 0.2.0 (released 2021-06-18)
===================================

* Add freeze command (#95)
* Add patch option (#22)
* Fix second update fails with non-standard SVN repo's (#167)
* Don't retain licenses in subfolders (#178)
* Import unpinned and non-std svn externals (#133)

Release 0.1.1 (released 2021-05-27)
===================================

* Fix empty folder remains after using ``src:`` with subfolder in git (#163)
* New logo

Release 0.1.0 (released 2021-05-13)
===================================

* Support for non-standard SVN repositories (#135)
* Fix `dst` usage for single source file with git (#120)

Release 0.0.9 (released 2021-03-16)
===================================

* Add copyright notices to documentation
* Make it possible to check/update child-projects (#99)
* Keep license files from repo, even when only checking only subdir (#50)
* Guard against overwriting local changes (#93)
* Add ``--force`` flag to ``dfetch update``

Release 0.0.8 (released 2021-02-14)
===================================

* Fix wrong version check (#101)
* Don't mandate remote section in manifest (#102)

Release 0.0.7 (released 2021-02-13)
===================================

* Add ``tag:`` attribute to manifest (#92)
* Remove branches/tags prefix for svn in manifest (#88)
* Branch name missing when not in manifest (#82)
* Interpret tags when checking for updates (#46)
* Add feature tests (#84)

Release 0.0.6 (released 2021-02-03)
===================================

* Make import command available for svn projects with externals.
* Improve documentation.
* Fix #73: Don't fail if svn or git is not installed.
* Fix #74: Don't default to SVN for non-ssh url.
* Add ``vcs:`` field to manifest.
* Make ``src:`` partial checkouts available for git.
* Drop support for shortened git sha (#80).

Release 0.0.5 (released 2021-01-05)
===================================

* Fix ``dfetch import`` command.
* Improve template.
* If no ``dst`` is given for a project, use name of project instead.
* Fixes #28: Rename manifest.yaml to dfetch.yaml

Release 0.0.4 (released 2020-11-12)
===================================

* Increase readability in terminals.
* Fix template generated by ``dfetch init``.

Release 0.0.3 (released 2020-11-09)
===================================

* Added release procedure.
* Added ``import`` command.

Release 0.0.2 (released 2020-11-03)
===================================

* Added ``dfetch environment`` command.
* Added changelog.


Release 0.0.1 (released 2020-11-03)
===================================

* Initial release

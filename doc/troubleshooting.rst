

Troubleshooting
===============

Sometimes *Dfetch* may not behave as expected. This is could be because it relies on
standard command-line tools such as ``git`` to be available on your system. This section will help you
diagnose problems and understand what is happening behind the scenes.

Step 1: Check your environment
------------------------------

Before anything else, it's helpful to see which tools *Dfetch* can detect on your system.
This shows missing or incompatible dependencies. Run:

.. code-block:: bash

    dfetch environment

Compare the output to the expected tools your commands require.

.. asciinema:: asciicasts/environment.cast

Step 2: Use verbose mode
------------------------

If a specific *Dfetch* command gives unexpected results, run it with the ``-v`` flag
to see exactly what *Dfetch* is doing:

.. code-block:: bash

    dfetch -v import

Verbose output shows each command *Dfetch* executes and its result, making it easier
to spot errors, missing tools, or other issues.
There can be various issues with for instance contacting or authenticating with the remote
repository or with local settings. By running the ``git`` or ``svn`` command in isolation
the issue can be shown more clearly.

Step 3: Reporting issues
------------------------

If you cannot resolve a problem, we're happy to help! Check for any existing `GitHub Issues`_.
When reporting an issue, please include:

1. The output of ``dfetch environment``
2. The verbose output of the failing command (``dfetch -v <command>``)
3. Your operating system and shell information

You can report issues via:

- `GitHub Issues`_
- `Gitter`_ community chat

.. _`GitHub Issues`: https://github.com/dfetch-org/dfetch/issues
.. _`Gitter`: https://gitter.im/dfetch-org/community


Security issues
----------------

If you discover a security vulnerability in *Dfetch*, please let us know right away and don't post a public issue.
You can report issues by opening a confidential issue via `GitHub Security Advisories`_. See
`GitHub's private vulnerability reporting`_ for more info. If you have no contact please contact us through
the mail listed in the pyproject.toml.

.. _`GitHub Security Advisories`: https://github.com/dfetch-org/dfetch/security/advisories
.. _`GitHub's private vulnerability reporting`: https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)

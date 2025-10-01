.. Dfetch documentation master file

Troubleshooting
===============

Although we do our best, *Dfetch* can always do something unexpected.
A great deal of *Dfetch* functionality is dependent on plain-old command line commands.

First of all, it is important to see what tools the system has.
This can be seen with :ref:`dfetch environment<environment>`.

Each command *Dfetch* performs and its result can be shown with increasing the verbosity
with the `-v` flag. For example, if an :ref:`dfetch import<import>` is giving strange results, re-run it with::

    dfetch -v import

Reporting issues
----------------
We are glad to help, if you you are stuck, either create an issue_ on github or contact us through gitter_!

.. _issue: https://github.com/dfetch-org/dfetch/issues
.. _gitter: https://gitter.im/dfetch-org/community

Security issues
----------------

If you discover a security vulnerability in *Dfetch*, please let us know right away and don't post a public issue.
You can report issues by opening a confidential issue via `GitHub Security Advisories`_. See
`GitHub's private vulnerability reporting`_ for more info. If you have no contact please contact us through
the mail listed in the pyproject.toml.

.. _`GitHub Security Advisories`: https://github.com/dfetch/dfetch/security/advisories
.. _`GitHub's private vulnerability reporting`: https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)

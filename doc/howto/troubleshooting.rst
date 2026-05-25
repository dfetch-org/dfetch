

Troubleshoot
============

Sometimes *Dfetch* may not behave as expected. This could be because it relies on
standard command-line tools such as ``git`` to be available on your system. This section will help you
diagnose problems and understand what is happening behind the scenes.

Step 1: Check your environment
------------------------------

Before anything else, it's helpful to see which tools *Dfetch* can detect on your system.
This shows missing or incompatible dependencies. Run:

.. code-block:: bash

    $ dfetch environment

Compare the output to the expected tools your commands require.

.. asciinema:: ../asciicasts/environment.cast

Step 2: Use verbose mode
------------------------

If a specific *Dfetch* command gives unexpected results, run it with the ``-v`` flag
to see exactly what *Dfetch* is doing:

.. code-block:: bash

    $ dfetch -v import

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


Using remotes over SSH
----------------------

*Dfetch* runs all ``git`` and ``svn`` commands in non-interactive mode, so it works
reliably in scripts and CI without hanging on a prompt. For SSH remotes (such as
``git@github.com:...`` or ``svn+ssh://...``) this means SSH runs with
``BatchMode=yes``: authentication happens without typing a password and the host key
needs to be trusted beforehand. You can prepare your environment once:

1. Trust the host key, for example:

   .. code-block:: bash

       $ ssh-keyscan svn.example.com >> ~/.ssh/known_hosts

2. Use key-based authentication, for example by loading your key into the
   ``ssh-agent``:

   .. code-block:: bash

       $ eval "$(ssh-agent)" && ssh-add ~/.ssh/my_key

   or by configuring the key per host in ``~/.ssh/config``.

If you need specific SSH options, you can set the ``GIT_SSH_COMMAND`` (git also honors
``core.sshCommand``) or ``SVN_SSH`` environment variables; *Dfetch* respects them and
only adds ``BatchMode=yes`` when you haven't configured ``BatchMode`` yourself:

.. code-block:: bash

    $ export GIT_SSH_COMMAND="ssh -i ~/.ssh/my_key"
    $ export SVN_SSH="ssh -i ~/.ssh/my_key"

After this, SSH projects fetch just like any other remote.


Security issues
----------------

If you discover a security vulnerability in *Dfetch*, please let us know right away and don't post a public issue.
You can report issues by opening a confidential issue via `GitHub Security Advisories`_. See
`GitHub's private vulnerability reporting`_ for more info. If you have no contact please contact us through
the mail listed in the pyproject.toml.

.. _`GitHub Security Advisories`: https://github.com/dfetch-org/dfetch/security/advisories
.. _`GitHub's private vulnerability reporting`: https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)

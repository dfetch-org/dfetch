

.. _line-endings:

Line Endings
============

Line endings affect the on-disk bytes of every text file.  For vendored code
this matters in two ways: tools and compilers on Windows may require CRLF, and
*Dfetch* hashes the directory after fetching to detect local modifications.  A
file with LF endings has a different hash from the same file with CRLF endings,
so fixing the line-ending style at fetch time prevents ``dfetch check`` from
reporting false local modifications.


Where the preference comes from
--------------------------------

*Dfetch* reads the line-ending preference from the **superproject** that owns
the manifest.  There is no separate dfetch setting.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Superproject type
     - Where the preference comes from
   * - Git
     - ``.gitattributes`` in the superproject root,
       e.g. ``* text=auto eol=lf``
   * - SVN
     - ``svn:auto-props`` on the superproject working copy,
       e.g. ``* = svn:eol-style=LF``

The preference is resolved for a hypothetical file inside the dependency's
destination directory, so directory-level rules such as
``vendor/mylib/* text=auto eol=lf`` are picked up correctly.

If no preference is found, *Dfetch* leaves line endings as the remote provides
them.


What happens on fetch
----------------------

The table below shows what ends up on disk for each combination of remote
content and superproject preference.

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Remote has
     - Superproject wants
     - Result on disk
   * - LF
     - lf
     - LF (no conversion needed)
   * - LF
     - crlf
     - CRLF (converted during checkout)
   * - CRLF
     - lf
     - LF (renormalized after checkout)
   * - CRLF
     - crlf
     - CRLF (no conversion needed)
   * - CRLF in ``*.bat`` with remote ``*.bat eol=crlf``
     - lf
     - CRLF (remote per-file attribute wins, see below)
   * - any
     - (none)
     - unchanged


Remote per-file attributes take precedence
-------------------------------------------

The superproject preference is a default, not an override.  If the remote
declares per-file line-ending rules in its own ``.gitattributes``, those rules
win for the files they cover.

A common case is Windows batch files.  A remote might have::

    # .gitattributes in the remote repo
    * text=auto
    *.bat eol=crlf
    *.cmd eol=crlf

Even when the superproject requests ``eol=lf``, ``.bat`` and ``.cmd`` files
keep their CRLF endings.  Files that have no explicit ``eol=`` attribute in the
remote fall back to the superproject preference.

Binary files are never converted regardless of any attribute.


Effect on the integrity hash
-----------------------------

The hash in ``.dfetch_data.yaml`` is computed from the files **after**
line-ending conversion.  Running ``dfetch update`` twice on the same remote
version always produces the same hash because the on-disk content is identical.

Changing the superproject's line-ending preference and running ``dfetch update``
again will produce a different hash.  The vendored files have genuinely changed,
so this is expected.  Running ``dfetch update`` after a preference change
re-aligns the hash with the new on-disk content.


Examples
--------

.. scenario-include:: ../features/superproject-line-ending-attrs.feature

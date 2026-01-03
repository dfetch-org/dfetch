

Alternatives
============
The problem *Dfetch* tries to solve isn't new. There are other tools doing the same.
In making a proper choice, see the below alternatives.

There are many alternatives, each with slightly different approaches or focuses: some are designed to manage
multiple repositories together, some are specialized in :ref:`vendoring` code into your project, and others provide
build-system or version-control-specific helpers.

Below is a list of notable tools along with their supported version control systems, platforms, and compatibility.

========================= ===== ===== ========= ======= =================== =======================
 Name                      Git   SVN   Windows   Linux   Language Agnostic   Build System Agnostic
------------------------- ----- ----- --------- ------- ------------------- -----------------------
Dfetch_                     ✔    ✔       ✔        ✔             ✔                   ✔
========================= ===== ===== ========= ======= =================== =======================
`Braid`_                    ✔    ✘       ✔        ✔             ✔                   ✔
`CGet`_                     ✔    ✘       ✔        ✔         ✘ (C/C++)             ✘ (CMake)
`CMake ExternalProject`_    ✔    ✘       ✔        ✔         ✘ (C/C++)             ✘ (CMake)
`Combo-layer`_              ✔    ✘       ✔        ✔         ✘ (C/C++)             ✘ (CMake)
`CPM.cmake`_                ✔    ✘       ✔        ✔         ✘ (C/C++)             ✘ (CMake)
`CPPAN`_                    ✔    ✘       ✔        ✔         ✘ (C/C++)               ✔
`degasolv`_                 ✔    ✘       ✔        ✔             ✔                   ✔
`depman`_                   ✔    ✘       ✔        ✔             ✔                   ✔
`depman bitrise`_           ✔    ✘       ✘        ✔             ✔                   ✔
`Garden`_                   ✔    ✘       ✘        ✔             ✔                   ✔
`gil`_                      ✔    ✘       ✔        ✔             ✔                   ✔
`Git submodules`_           ✔    ✘       ✔        ✔             ✔                   ✔
`Git subtree`_              ✔    ✘       ✔        ✔             ✔                   ✔
`Git X-modules`_            ✔    ✘       ✔        ✔             ✔                   ✔
`git-aggregator`_           ✔    ✘       ✔        ✔             ✔                   ✔
`Git-externals`_            ✔    ✘       ✔        ✔             ✔                   ✔
`git-toprepo`_              ✔    ✘       ✔        ✔             ✔                   ✔
`git-vendor`_               ✔    ✘       ✔        ✔             ✔                   ✔
`Giternal`_                 ✔    ✘       ✔        ✔             ✔                   ✔
`Gitman`_                   ✔    ✘       ✔        ✔             ✔                   ✔
`Gitslave`_                 ✔    ✘       ✘        ✔             ✔                   ✔
`Google Repo`_              ✔    ✘       ✔        ✔             ✔                   ✔
`Grit`_                     ✔    ✘       ✔        ✔             ✔                   ✔
`Hemlock`_                  ✔    ✘       ✔        ✔             ✔                   ✔
`josh`_                     ✔    ✘       ✔        ✔             ✔                   ✔
`Kitenet mr`_               ✔    ✔       ?         ✔             ✔                   ✔
`mdlr`_                     ✔    ✘       Beta      ✔             ✔                   ✔
`myrepos`_                  ✔    ✘       ✘        ✔             ✔                   ✔
`OpenTitan-vendor.py`_      ✔    ✘       ✘        ✔             ✔                   ✔
`pasta`_                    ✔    ✘       ✔        ✔             ✔                   ✔
`peru`_                     ✔    ✘       ✔        ✔             ✔                   ✔
`Quack`_                    ✔    ✘       ✘        ✔             ✔                   ✔
`Quark`_                    ✔    ✔       ✔        ✔             ✔                   ✔
`SoftwareNetwork`_          ✔    ✘       ✔        ✔         ✘ (C/C++)               ✔
`subpatch`_                 ✔    ✘       ✔        ✔             ✔                   ✔
`SVN Externals`_            ✘    ✔       ✔        ✔             ✔                   ✔
`svn_xternals`_             ✘    ✔       ✔        ✔             ✔                   ✔
`tsrc`_                     ✔    ✘       ✔        ✔             ✔                   ✔
`Vcpkg`_                    ✔    ✘       ✔        ✔         ✘ (C/C++)               ✘
`Vcsh`_                     ✔    ✘       ✘        ✔             ✔                   ✔
`vdm`_                      ✔    ✘       ✔        ✔             ✔                   ✔
`vendor-go`_                ✔    ✘       ✔        ✔             ✔                   ✔
`vendorpull`_               ✔    ✘       ✘        ✔             ✔                   ✔
`verde`_                    ✔    ✘       ✔        ✔             ✔                   ✔
`vndr`_                     ✔    ✘       ✔        ✔             ✔                   ✔
`West`_                     ✔    ✘       ✔        ✔         ✘ (C/C++)               ✘
========================= ===== ===== ========= ======= =================== =======================

.. _`Dfetch`: https://github.com/dfetch-org/dfetch

.. _`Braid`: https://github.com/cristibalan/braid
.. _`CGet`: https://github.com/pfultz2/cget
.. _`CMake ExternalProject`: https://cmake.org/cmake/help/latest/module/ExternalProject.html
.. _`Combo-layer`: https://wiki.yoctoproject.org/wiki/Combo-layer
.. _`CPM.cmake`: https://github.com/cpm-cmake/CPM.cmake
.. _`CPPAN`: https://github.com/cppan/cppan
.. _`degasolv`: https://github.com/djha-skin/degasolv
.. _`depman`: https://github.com/depman-org/depman
.. _`depman bitrise`: https://github.com/bitrise-io/depman
.. _`Garden`: https://github.com/davvid/garden
.. _`gil`: https://github.com/chronoxor/gil
.. _`Git submodules`: https://git-scm.com/book/en/v2/Git-Tools-Submodules
.. _`Git subtree`: https://www.atlassian.com/git/tutorials/git-subtree
.. _`Git X-modules`: https://subgit.com/gitx
.. _`git-aggregator`: https://github.com/acsone/git-aggregator
.. _`Git-externals`: https://github.com/develer-staff/git-externals
.. _`git-toprepo`: https://github.com/meroton/git-toprepo
.. _`git-vendor`: https://github.com/brettlangdon/git-vendor
.. _`Giternal`: https://github.com/patmaddox/giternal
.. _`Gitman`: https://github.com/jacebrowning/gitman
.. _`Gitslave`: http://gitslave.sourceforge.net/
.. _`Google Repo`: https://android.googlesource.com/tools/repo
.. _`Grit`: https://github.com/rabarberpie/grit
.. _`Hemlock`: https://github.com/MadL1me/hemlock
.. _`josh`: https://github.com/josh-project/josh
.. _`Kitenet mr`: https://github.com/toddr/kitenet-mr
.. _`mdlr`: https://github.com/exlinc/mdlr
.. _`myrepos`: http://myrepos.branchable.com/
.. _`OpenTitan-vendor.py`: https://github.com/lowRISC/opentitan/blob/master/util/vendor.py
.. _`pasta`: https://github.com/audiotool/pasta
.. _`peru`: https://github.com/buildinspace/peru
.. _`Quack`: https://github.com/autodesk/quack
.. _`Quark`: https://github.com/comelz/quark
.. _`SoftwareNetwork`: https://github.com/SoftwareNetwork/sw
.. _`subpatch`: https://github.com/lengfeld/subpatch
.. _`SVN externals`: https://tortoisesvn.net/docs/release/TortoiseSVN_en/tsvn-dug-externals.html
.. _`svn_xternals`: https://github.com/fviard/svn_xternals
.. _`tsrc`: https://github.com/dmerejkowsky/tsrc
.. _`Vcpkg`: https://github.com/Microsoft/vcpkg
.. _`Vcsh`: https://github.com/RichiH/vcsh
.. _`vdm`: https://github.com/opensourcecorp/vdm
.. _`vendor-go` : https://github.com/alevinval/vendor-go
.. _`vendorpull`: https://github.com/sourcemeta/vendorpull
.. _`verde` : https://github.com/aramtech/verde
.. _`vndr` : https://github.com/LK4D4/vndr
.. _`West`: https://docs.zephyrproject.org/latest/guides/west/index.html

.. note:: the list is probably never complete or up-to-date. Anyone is welcome to create an issue_.

.. _issue: https://github.com/dfetch-org/dfetch/issues

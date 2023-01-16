.. Dfetch documentation master file

Alternatives
============
The problem *Dfetch* tries to solve isn't new. There are other tools doing the same.
In making a proper choice, see the below alternatives.

These alternatives could all be used to use *source* code from another project as part
of your project.

========================= ===== ===== ========= ======= =================== =======================
 Name                      Git   SVN   Windows   Linux   Language Agnostic   Build System Agnostic
------------------------- ----- ----- --------- ------- ------------------- -----------------------
Dfetch_                     ✔    ✔       ✔        ✔             ✔                   ✔
========================= ===== ===== ========= ======= =================== =======================
`CGet`_                     ✔    ✘       ✔        ✔         ✘ (C/C++)             ✘ (CMake)
`CMake ExternalProject`_    ✔    ✘       ✔        ✔         ✘ (C/C++)             ✘ (CMake)
`CPM.cmake`_                ✔    ✘       ✔        ✔         ✘ (C/C++)             ✘ (CMake)
`CPPAN`_                    ✔    ✘       ✔        ✔         ✘ (C/C++)               ✔
`Git submodules`_           ✔    ✘       ✔        ✔             ✔                   ✔
`Git subtree`_              ✔    ✘       ✔        ✔             ✔                   ✔
`Git-externals`_            ✔    ✘       ✔        ✔             ✔                   ✔
`Gitman`_                   ✔    ✘       ✔        ✔             ✔                   ✔
`Gitslave`_                 ✔    ✘       ✘        ✔             ✔                   ✔
`Google Repo`_              ✔    ✘       ✔        ✔             ✔                   ✔
`Grit`_                     ✔    ✘       ✔        ✔             ✔                   ✔
`Kitenet mr`_               ✔    ✔       ?         ✔             ✔                   ✔
`mdlr`_                     ✔    ✘       Beta      ✔             ✔                   ✔
`Quack`_                    ✔    ✘       ✘        ✔             ✔                   ✔
`Quark`_                    ✔    ✔       ✔        ✔             ✔                   ✔
`SVN Externals`_            ✘    ✔       ✔        ✔             ✔                   ✔
`tsrc`_                     ✔    ✘       ✔        ✔             ✔                   ✔
`SoftwareNetwork`_          ✔    ✘       ✔        ✔         ✘ (C/C++)               ✔
`Vcpkg`_                    ✔    ✘       ✔        ✔         ✘ (C/C++)               ✘
`West`_                     ✔    ✘       ✔        ✔         ✘ (C/C++)               ✘
========================= ===== ===== ========= ======= =================== =======================

.. _`CGet`: https://github.com/pfultz2/cget
.. _`CMAke ExternalProject`: https://cmake.org/cmake/help/latest/module/ExternalProject.html
.. _`CPM.cmake`: https://github.com/cpm-cmake/CPM.cmake
.. _`CPPAN`: https://github.com/cppan/cppan
.. _`Dfetch`: https://github.com/dfetch-org/dfetch
.. _`Git submodules`: https://git-scm.com/book/en/v2/Git-Tools-Submodules
.. _`Git subtree`: https://www.atlassian.com/git/tutorials/git-subtree
.. _`Git-externals`: https://github.com/develer-staff/git-externals
.. _`Gitman`: https://github.com/jacebrowning/gitman
.. _`Gitslave`: http://gitslave.sourceforge.net/
.. _`Google Repo`: https://android.googlesource.com/tools/repo
.. _`Grit`: https://github.com/rabarberpie/grit
.. _`Kitenet mr`: https://github.com/toddr/kitenet-mr
.. _`mdlr`: https://github.com/exlinc/mdlr
.. _`Quack`: https://github.com/autodesk/quack
.. _`Quark`: https://github.com/comelz/quark
.. _`SVN externals`: https://tortoisesvn.net/docs/release/TortoiseSVN_en/tsvn-dug-externals.html
.. _`tsrc`: https://github.com/dmerejkowsky/tsrc
.. _`SoftwareNetwork`: https://github.com/SoftwareNetwork/sw
.. _`Vcpkg`: https://github.com/Microsoft/vcpkg
.. _`West`: https://docs.zephyrproject.org/latest/guides/west/index.html

.. note:: the list is probably never complete or up-to-date. Anyone is welcome to create an issue_.

.. _issue: https://github.com/dfetch-org/dfetch/issues

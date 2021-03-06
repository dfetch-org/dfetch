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
Dfetch_                     ✅   ✅     ✅       ✅          ✅                   ✅
========================= ===== ===== ========= ======= =================== =======================
`CMake ExternalProject`_    ✅   ❌     ✅       ✅      ❌ (C/C++)             ❌ (CMake)
`CPM.cmake`_                ✅   ❌     ✅       ✅      ❌ (C/C++)             ❌ (CMake)
`Git submodules`_           ✅   ❌     ✅       ✅          ✅                   ✅
`Git subtree`_              ✅   ❌     ✅       ✅          ✅                   ✅
`Gitslave`_                 ✅   ❌     ❌       ✅          ✅                   ✅
`Google Repo`_              ✅   ❌     ✅       ✅          ✅                   ✅
`Grit`_                     ✅   ❌     ✅       ✅          ✅                   ✅
`Kitenet mr`_               ✅   ✅     ?        ✅          ✅                   ✅
`mdlr`_                     ✅   ❌     Beta     ✅          ✅                   ✅
`Quack`_                    ✅   ❌     ❌       ✅          ✅                   ✅
`SVN Externals`_            ❌   ✅     ✅       ✅          ✅                   ✅
`tsrc`_                     ✅   ❌     ✅       ✅          ✅                   ✅
`Vcpkg`_                    ✅   ❌     ✅       ✅      ❌ (C/C++)             ❌ (CMake)
`West`_                     ✅   ❌     ✅       ✅      ❌ (C/C++)             ❌ (CMake)
========================= ===== ===== ========= ======= =================== =======================

.. _`CMAke ExternalProject`: https://cmake.org/cmake/help/latest/module/ExternalProject.html`
.. _`CPM.cmake`: https://github.com/cpm-cmake/CPM.cmake
.. _`Dfetch`: https://github.com/dfetch-org/dfetch
.. _`Git submodules`: https://git-scm.com/book/en/v2/Git-Tools-Submodules
.. _`Git subtree`: https://www.atlassian.com/git/tutorials/git-subtree
.. _`Gitslave`: http://gitslave.sourceforge.net/
.. _`Google Repo`: https://android.googlesource.com/tools/repo
.. _`Grit`: https://github.com/rabarberpie/grit
.. _`Kitenet mr`: https://github.com/toddr/kitenet-mr
.. _`mdlr`: https://github.com/exlinc/mdlr
.. _`Quack`: https://github.com/autodesk/quack
.. _`SVN externals`: https://tortoisesvn.net/docs/release/TortoiseSVN_en/tsvn-dug-externals.html
.. _`tsrc`: https://github.com/dmerejkowsky/tsrc
.. _`Vcpkg`: https://github.com/Microsoft/vcpkg
.. _`West`: https://docs.zephyrproject.org/latest/guides/west/index.html

.. note:: the list is probably never complete or up-to-date. Anyone is welcome to create an issue_.

.. _issue: https://github.com/dfetch-org/dfetch/issues

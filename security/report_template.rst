.. ============================================================
.. Auto-generated file — do not edit manually.
.. Regenerate with (see security/README.md for exact commands):
..
..   python -m security.tm_<supply_chain|usage> \
..       --report security/report_template.rst \
..       > doc/explanation/threat_model_<name>.rst
.. ============================================================

System Description
------------------

{tm.description}

Assumptions
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Description
{tm.assumptions:repeat:
   * - {{item.name}}
     - {{item.description}}
}

Dataflows
---------

.. list-table::
   :header-rows: 1
   :widths: 35 20 20 25

   * - Name
     - From
     - To
     - Protocol
{dataflows:repeat:
   * - {{item.display_name:call:}}
     - {{item.source.name}}
     - {{item.sink.name}}
     - {{item.protocol}}
}

Data Dictionary
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Name
     - Description
     - Classification
{data:repeat:
   * - {{item.name}}
     - {{item.description}}
     - {{item.classification.name}}
}

Actors
------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Name
     - Description
{actors:repeat:
   * - {{item.name}}
     - {{item.description}}
}

Boundaries
----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Name
     - Description
{boundaries:repeat:
   * - {{item.name}}
     - {{item.description}}
}

Assets
------

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Name
     - Description
     - Type
{assets:repeat:
   * - {{item.name}}
     - {{item.description}}
     - {{item:call:getElementType}}
}

{tm.excluded_findings:if:
Excluded Threats
----------------

.. list-table::
   :header-rows: 1
   :widths: 12 28 20 20 8 12

   * - ID
     - Description
     - Target
     - Assumption
     - Severity
     - References
}
{tm.excluded_findings:repeat:
   * - {{item:call:getThreatId}}
     - {{item:call:getFindingDescription}}
     - {{item:call:getFindingTarget}}
     - {{item.assumption.name}}
     - {{item:call:getFindingSeverity}}
     - {{item:call:getFindingReferences}}
}

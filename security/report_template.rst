.. ============================================================
.. Auto-generated file — do not edit manually.
.. Regenerate with (see security/README.md for exact commands):
..
..   python -m security.tm_<supply_chain|usage> \
..       --report security/report_template.rst \
..       > doc/explanation/threat_model_<name>.rst
..
.. ============================================================

Risk Context
------------

This report follows the risk-based approach of `BSI TR-03183-1
<https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TR03183/BSI-TR-03183-1.pdf>`_
Chapter 5.
The Sev / Risk rating scale and treatment vocabulary (Mitigate / Accept / Transfer)
are defined in the :ref:`Risk Rating Methodology <security>` section of the main security page.

{tm.description}

Assumptions
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70
   :width: 100%

   * - Name
     - Description
{tm.assumptions:repeat:
   * - {{item.name}}
     - {{item.description}}
}

Actors
------

.. list-table::
   :header-rows: 1
   :widths: 25 75
   :width: 100%

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
   :width: 100%

   * - Name
     - Description
{boundaries:repeat:
   * - {{item.name}}
     - {{item.description}}
}

Data Flow Diagram
-----------------

{{dfd_content}}

Sequence Diagram
----------------

{{seq_content}}

Asset Identification
--------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 13 17
   :width: 100%

   * - Name
     - Description
     - Type
     - C / I / A
{{assets_rows}}

{tm.excluded_findings:if:
Excluded / Accepted Risks
-------------------------

The following threats are excluded from active treatment, each linked to
the assumption under which the risk is considered acceptable.

.. list-table::
   :header-rows: 1
   :widths: 12 28 20 20 8 12
   :width: 100%

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

Dataflows
---------

.. list-table::
   :header-rows: 1
   :widths: 35 20 20 25
   :width: 100%

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

Threats
-------

.. list-table::
   :header-rows: 1
   :widths: 10 22 18 15 34
   :width: 100%

   * - ID
     - Description
     - Target
     - Analysis
     - Controls / Notes
{{threats_rows}}

Controls
--------

.. list-table::
   :header-rows: 1
   :widths: 8 25 15 52
   :width: 100%

   * - ID
     - Name
     - Threats
     - Description
{{controls_rows}}

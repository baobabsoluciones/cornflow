Examples of solution methods
------------------------------------

In this section we list the public examples in the `cornflow-dags <https://github.com/baobabsoluciones/cornflow/tree/master/cornflow-dags>`_ part of the repository.

In order to use any of the examples, check the :ref:`User your solution method` section and put the "dag name" when asked for the schema argument. Also, the solver name needs to be included in the ``solver`` property in the configuration of the execution. If not, the default solver will be used. The names of the available solvers can be found when downloading the schema (see :py:meth:`cornflow_client.cornflow_client.CornFlow.get_schema`) or in the individual example page.


Current examples:

.. toctree::
    :maxdepth: 3

    bar_cutting
    facility_location
    graph_coloring
    knapsack
    roadef
    rostering
    scheduling
    tsp
    two_dimensional_bin_packing
    vrp


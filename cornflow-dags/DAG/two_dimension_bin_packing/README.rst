Two dimension bin packing
-----------------------------

A set of objects have to be place on a two dimension grid maximizing the value of the objects placed on the grid. This problem is an extension of the bin packing problem. The bin packing problem is a combinatorial NP-hard problem. The two dimension bin packing problem is also NP-hard.

**Name of the DAG**: `two_dimension_bin_packing`

**Available solution methods**:

- **default**: A mip solver.
- right_corner: The mip solver based on coordinates of the right corner. It can be solved with CBC, Gurobi or SCIP.

Decision
========

For each object we have to decide if it is included on the bin and its position inside of it maximizing the value of the items placed on the bin.

Input data
===========

- Items: A set of items with their width, height and value.

- Parameters:

  - width: The width of the bin.
  - height: The height of the bin.
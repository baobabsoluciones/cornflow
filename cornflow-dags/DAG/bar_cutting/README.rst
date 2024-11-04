Bar cutting
------------

The problem consists of cutting a rod of length n into different pieces of products based on the demand of each one of them and an available set of cutting patterns to be used.

**Name of the DAG**: bar_cutting

**Available solution methods**:

- **default**: mip solver
- mip: mip solver that can be solved with CBC or Gurobi.
- CG: column generation solver that can be solved with CBC or Gurobi.

Decision
=========

The number of products per bar and pattern in order to satisfy the demand of each product.

Input data
===========

- Bars: List of bars available for cutting and their length.
- Products: List of products that can be produced and their length.
- Demand: List of demand for each product.
- Cutting patterns: List o available cutting patters per bar. The mip solver uses the ones established here, while the CG solver generates them from this initial list.
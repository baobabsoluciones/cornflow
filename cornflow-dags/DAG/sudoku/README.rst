Sudoku
=======================

The problem consists on finding a set of values that:
(1) comply with the "sudoku rules": all unique in each (a) row, (b) column and (c) square (for a 9x9 sudoku that is) and
(2) comply with the initial values given at specific places in the grid.

There is usually no objective function: this is a feasibility problem.

**Name of dag**: sudoku

**Available solution methods**:

- **cp_sat:** CP model built in ortools with CP-SAT as solver.
- **mip:** MIP model built in pulp and solved with cbc.


Decision
------------

For each row i and column j which value p.

Parameters
------------

- Initial values per row and column.
- Parameters: size of sudoku (9 by default).

Thanks
--------

To Peter Norvig for the datasets: https://github.com/norvig/pytudes/blob/main/py
To Alain T. for the print visualization: https://stackoverflow.com/a/56581709/6508131
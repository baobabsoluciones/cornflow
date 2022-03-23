Vehicle Routing Problem
==========================

The problem consists on scheduling routes to vehicles in order to deliver goods to each customer while minimizing the total distance. There are many variants of this problem. The current implementation solves the Capacitated VRP (CVRP) where vehicles have a max capacity of goods to deliver.

**Name of dag**: vrp

**Available solution methods**:

* **algorithm1**: Dumb heuristic that chooses the closest neighbor at each time. Does not use capacity.
* **algorithm2**: Dumb heuristic that chooses the closes neighbor at each time. Takes capacity into account.
* **algorithm3**: CP model built in ortools with CP-SAT as solver.



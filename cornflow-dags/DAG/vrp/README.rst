Vehicle Routing Problem (VRP)
------------------------------------

We want to schedule delivery routes to cover the demand of a given set of customers subject to capacity constraints in each vehicle. We want to satisfy all customers requirements by minimizing the total distance traveled.

Each route has to start and end in one depot.

**Name of dag**: ``vrp

**Available solution methods**:

- algorithm1: dumb heuristic that chooses the closest neighbor at each time. Does not use capacity.
- algorithm2: dumb heuristic that chooses the closes neighbor at each time. Takes capacity into account.
- algorithm3: a constraint programming built in ortools with CP-SAT as solver.
- mip: a MIP model implemented on Pyomo.

Decision
============

A set of routes. Each route consists of an ordered list of clients to visit.

Parameters
============

* Weighted edges of the Graph. Each edge represent the distance between its pair of nodes.
* Demand for each customer.
* Capacity of each vehicle.
* A set of nodes that are depots.

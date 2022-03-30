Problem
------------

We want to schedule delivery routes to cover the demand of a given set of customers subject to capacity constraints in each vehicle. We want to satisfy all customers requirements by minimizing the total distance traveled.

Each route has to start and end in one depot.

Decision
------------

A set of routes. Each route consists of an ordered list of clients to visit.

Parameters
------------

* Weighted edges of the Graph. Each edge represent the distance between its pair of nodes.
* Demand for each customer.
* Capacity of each vehicle.
* A set of nodes that are depots.

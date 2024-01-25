Travelling Salesman Problem (TSP)
------------------------------------

We want to find the shortest tour that visits each node in a Graph once.

**Name of the dag**: tsp

**Available solution methods**:

- **default**: naive solver.
- naive: naive solver. It is the default method.
- cpsat: a constraint programming solver implemented with Google's ORTools.

Decision
=========

An ordered list of the nodes to visit.

Parameters
===========

- Weighted edges of the Graph. Each edge represents the distance between its pair of nodes.

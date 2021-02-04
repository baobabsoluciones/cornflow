Concepts
==========================


Decision (Optimization) problem
----------------------------------

A quote from the first paragraph of the `Wikipedia article on Decision problem <https://en.wikipedia.org/wiki/Decision_problem>`_:

    In computability theory and computational complexity theory, a decision problem is a problem that can be posed as a yes-no question of the input values. An example of a decision problem is deciding whether a given natural number is prime. Another is the problem "given two numbers x and y, does x evenly divide y?". The answer is either 'yes' or 'no' depending upon the values of x and y. A method for solving a decision problem, given in the form of an algorithm, is called a decision procedure for that problem. A decision procedure for the decision problem "given two numbers x and y, does x evenly divide y?" would give the steps for determining whether x evenly divides y. One such algorithm is long division. If the remainder is zero the answer is 'yes', otherwise it is 'no'. A decision problem which can be solved by an algorithm is called decidable. 

In this guide, we do not make a clear difference between Decision problem and Optimization problem. In both cases we care on finding a solution (or the best solution) given a feasible solution space.

In Cornflow, we refer to this Decision Problem as an Abstract Problem or just Problem. Some Problems are quite famouse, such as the  (`Traveling Salesman Problem <https://en.wikipedia.org/wiki/Travelling_salesman_problem>`_) and the `Knapsack Problem <https://en.wikipedia.org/wiki/Knapsack_problem>`_. An Abstract Problem is useful because it can be used to design a Solution Method for that particular abstract problem.

In Cornflow, it is represented by two `schema` json file. The first one describes the input data format each Instance of the problem must follow in order for it to belong to the Abstract Problem. The second one describes the output data format each Solution of the problem must follow in order for it to belong to the Abstract Problem.

Instance
-----------------

An Instance is a particular case of a Problem. It represents all the data needed to completely formulate one case of a decision problem. 

In Cornflow, it is represented as a `data` json file. This file should be sufficient to represent the Feasible Solution Space and provide enough information to determine if one Solution to the problem is better or worse than another. We sometimes call it "Input Data".


Feasible Solution Space
-----------------------------

Is the set of all Solutions that are valid given an Instance of a Problem.


Solution
-----------

A Solution represents all data needed to completely represent a feasible solution to an Instance. 

In Cornflow, it is represented as a `data` json file. This file should be sufficient to, when used together with an Instance, determine if the solution is feasible and the Objective Function Value of the Solution. We sometimes call it "Output Data".


Experiment
-------------

This is just a convenient way to tie an Instance and a Solution together to be able to validate and compare solutions.


Solution Method
-------------------

A solution method (also called Algorithm) is a function that takes as input an Instance and returns a Solution. The Solution Method can be exact (it can prove it can find the best solution) or inexact (there is no proof).

In Cornflow, A Solution Method is a subclass of Experiment.


Solve Configuration
---------------------

Each Solution Method has ways to personalize certain characteristics.


Execution
-------------

Consists of: (1) an Instance with (2) a Solve Configuration and (3) a Solution Method. It is the actual solving of the Decision Problem. It returns a Solution.


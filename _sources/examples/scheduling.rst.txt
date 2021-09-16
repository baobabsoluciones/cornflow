Scheduling: hackathon
==========================

We want to schedule all jobs by deciding when and in which mode to execute each job. There are precedence relationships between pairs of jobs. There are two types of resources. Renewable resources (R) are consumed each period and have an availability that is recovered each period of time. Non-renewable resources (N) are consumed once per job and have an availability for the whole planning horizon. The objective is to reduce the finishing time (start time + duration) of the last job.

**Name of dag**: hk_2020_dag

**Available solution methods**:

* **ortools**: CP model built in ortools and solved with CP-SAT.
* **Iterator_HL**: Matheuristic built as a sequence of MIP models in Pyomo and solved with CBC.
* **loop_EJ**: Matheuristic built as a sequence of MIP models in Pyomo and solved with CBC. Does not guarantee a feasible solution.
* **default**: Simple heuristic that puts one task after the other. Does not guarantee a feasible solution.

The implementation of this solution method is mainly in another public repository: https://github.com/baobabsoluciones/hackathonbaobab2020

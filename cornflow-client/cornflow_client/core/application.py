from typing import Type, Dict, List, Tuple
from timeit import default_timer as timer
from .instance import InstanceCore
from .solution import SolutionCore
from .experiment import ExperimentCore
from abc import ABC, abstractmethod
from cornflow_client.constants import (
    STATUS_OPTIMAL,
    STATUS_NOT_SOLVED,
    STATUS_INFEASIBLE,
    STATUS_UNDEFINED,
    STATUS_TIME_LIMIT,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
)


class ApplicationCore(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def instance(self) -> Type[InstanceCore]:
        raise NotImplementedError()

    @property
    @abstractmethod
    def solution(self) -> Type[SolutionCore]:
        raise NotImplementedError()

    @property
    @abstractmethod
    def schema(self) -> dict:
        """
        returns the configuration schema used for the solve() method
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def test_cases(self) -> List[Dict]:
        raise NotImplementedError()

    @property
    @abstractmethod
    def solvers(self) -> Dict[str, Type[ExperimentCore]]:
        raise NotImplementedError()

    def solve(self, data: dict, config: dict) -> Tuple[Dict, str, Dict]:
        """
        :param data: json for the problem
        :param config: execution configuration, including solver
        :return: solution and log
        """
        print("Solving the model")
        solver = config.get("solver")
        if solver is None:
            solver = self.get_default_solver_name()
        solver_class = self.get_solver(name=solver)
        if solver_class is None:
            raise NoSolverException("Solver {} is not available".format(solver))
        inst = self.instance.from_dict(data)
        algo = solver_class(inst, None)
        start = timer()

        try:
            status = algo.solve(config)
            print("ok")
        except Exception as e:
            print("problem was not solved")
            print(e)
            status = 0

        sol = None
        status_conv = {
            STATUS_OPTIMAL: "Optimal",
            STATUS_TIME_LIMIT: "Time limit",
            STATUS_INFEASIBLE: "Infeasible",
            STATUS_UNDEFINED: "Unknown",
            STATUS_NOT_SOLVED: "Not solved",
        }
        log = dict(
            time=timer() - start,
            solver=solver,
            status=status_conv.get(status, "Unknown"),
            status_code=status,
            sol_code=SOLUTION_STATUS_INFEASIBLE,
        )
        # check if there is a solution
        # TODO: we need to extract the solution status too
        #  because there may be already an initial solution in the solver
        if algo.solution is not None and len(algo.solution.data):
            sol = algo.solution.to_dict()
            log["sol_code"] = SOLUTION_STATUS_FEASIBLE
        return sol, "", log

    def get_solver(self, name: str = "default") -> Type[ExperimentCore]:
        return self.solvers.get(name)

    def get_default_solver_name(self) -> str:
        return self.schema["properties"]["solver"]["default"]


class NoSolverException(Exception):
    pass

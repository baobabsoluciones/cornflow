from typing import Type, Dict, List, Tuple, Union
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
    """
    The application template.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Mandatory property

        :return: the name of the class.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def instance(self) -> Type[InstanceCore]:
        """
        Mandatory property

        :return: the constructor for the instance.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def solution(self) -> Type[SolutionCore]:
        """
        Mandatory property

        :return: the constructor for the solution.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def schema(self) -> dict:
        """
        Mandatory property

        :return: the configuration schema used for the solve() method.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def test_cases(self) -> List[Dict]:
        """
        Mandatory property

        :return: a list of datasets following the json-schema.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def solvers(self) -> Dict[str, Type[ExperimentCore]]:
        """
        Mandatory property

        :return: a dictionary of constructors for solution methods for this particular problem.
        """
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
            output = algo.solve(config)
            print("ok")
        except Exception as e:
            print("problem was not solved")
            print(e)
            output = dict(status=0)

        sol = None
        status_conv = {
            STATUS_OPTIMAL: "Optimal",
            STATUS_TIME_LIMIT: "Time limit",
            STATUS_INFEASIBLE: "Infeasible",
            STATUS_UNDEFINED: "Unknown",
            STATUS_NOT_SOLVED: "Not solved",
        }
        if isinstance(output, int):
            output = dict(status=output)
        status = output.get("status")
        status_sol = output.get("status_sol")
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
        if status_sol is not None:
            log["sol_code"] = status_sol
        elif algo.solution is not None and len(algo.solution.data):
            log["sol_code"] = SOLUTION_STATUS_FEASIBLE

        if log["sol_code"] > 0:
            sol = algo.solution.to_dict()
        return sol, "", log

    def get_solver(self, name: str = "default") -> Union[Type[ExperimentCore], None]:
        """
        :param name: name of the solver to find

        :return: the constructor for a solver matching the name
        """
        return self.solvers.get(name)

    def get_default_solver_name(self) -> str:
        """
        :return: the name of the default solver
        """
        return self.schema["properties"]["solver"]["default"]

    def get_schemas(self) -> Dict[str, Dict]:
        """
        :return: a dictionary with the three schemas that define the solution method
        """
        return dict(
            instance=self.instance.schema,
            solution=self.solution.schema,
            config=self.schema,
        )


class NoSolverException(Exception):
    pass

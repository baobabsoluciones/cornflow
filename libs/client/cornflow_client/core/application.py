"""

"""
# Partial imports
from abc import ABC, abstractmethod
from jsonschema import Draft7Validator
from timeit import default_timer as timer
from typing import Type, Dict, List, Tuple, Union

# Imports from internal modules
from .instance import InstanceCore
from .solution import SolutionCore
from .experiment import ExperimentCore

from cornflow_client.constants import (
    STATUS_OPTIMAL,
    STATUS_NOT_SOLVED,
    STATUS_INFEASIBLE,
    STATUS_UNDEFINED,
    STATUS_TIME_LIMIT,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
    NoSolverException,
    BadConfiguration,
    BadSolution,
    BadInstance,
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
    def description(self) -> Union[str, None]:
        """
        Optional property

        :return: the description of the class
        """
        return None

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
    def test_cases(self) -> List[Union[Dict, Tuple[Dict, Dict]]]:
        """
        Mandatory property

        :return: a list of datasets following the json-schema.
          if each element in the list is:

          * **dict**: each element is an instance
          * **tuple**: the first part is the instance, the second its solution
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

    def solve(
        self, data: dict, config: dict, solution_data: dict = None
    ) -> Tuple[Dict, Union[Dict, None], Union[Dict, None], str, Dict]:
        """
        :param data: json for the problem
        :param config: execution configuration, including solver
        :param solution_data: optional json with an initial solution
        :return: solution, solution checks, instance checks and logs
        """
        if config.get("msg", True):
            print("Solving the model")
        validator = Draft7Validator(self.schema)
        if not validator.is_valid(config):
            error_list = [e for e in validator.iter_errors(config)]
            raise BadConfiguration(
                "The configuration does not match the schema:\n{}".format(error_list)
            )

        solver = config.get("solver")
        if solver is None:
            solver = self.get_default_solver_name()
        solver_class = self.get_solver(name=solver)
        if solver_class is None:
            raise NoSolverException("Solver {} is not available".format(solver))
        inst = self.instance.from_dict(data)
        inst_errors = inst.check_schema()
        if inst_errors:
            raise BadInstance(
                "The instance does not match the schema:\n{}".format(inst_errors)
            )
        sol = None
        if solution_data is not None:
            sol = self.solution.from_dict(solution_data)
            sol_errors = sol.check_schema()
            if sol_errors:
                raise BadSolution(
                    "The solution does not match the schema:\n{}".format(sol_errors)
                )

        instance_checks = inst.check()
        if instance_checks:
            log = dict(
                time=0,
                solver=solver,
                status="Infeasible",
                status_code=STATUS_INFEASIBLE,
                sol_code=SOLUTION_STATUS_INFEASIBLE,
            )
            return dict(), None, instance_checks, "", log

        algo = solver_class(inst, sol)
        start = timer()
        output = algo.solve(config)
        sol = None
        status_conv = {
            STATUS_OPTIMAL: "Optimal",
            STATUS_TIME_LIMIT: "Time limit",
            STATUS_INFEASIBLE: "Infeasible",
            STATUS_UNDEFINED: "Unknown",
            STATUS_NOT_SOLVED: "Not solved",
        }
        # compatibility with previous format:
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

        checks = algo.check_solution()

        return sol, checks, {}, "", log

    def get_solver(self, name: str = "default") -> Union[Type[ExperimentCore], None]:
        """
        :param name: name of the solver to find

        :return: the constructor for a solver matching the name
        """
        if "." in name:
            solver = name.split(".")[0]
        else:
            solver = name
        return self.solvers.get(solver)

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

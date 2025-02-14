"""
Base code for the experiment template.
"""

import warnings
from abc import ABC, abstractmethod
from typing import Union, Dict

from jsonschema import Draft7Validator

from cornflow_client.constants import (
    PARAMETER_SOLVER_TRANSLATING_MAPPING,
    SOLVER_CONVERTER,
    BadSolutionChecks,
)
from .instance import InstanceCore
from .solution import SolutionCore


class ExperimentCore(ABC):
    """
    The solver template.
    """

    def __init__(
        self,
        instance: InstanceCore,
        solution: Union[SolutionCore, None] = None,
    ):
        # instance is read-only
        self._instance = instance
        self.solution = solution

    @property
    def instance(self) -> InstanceCore:
        """
        :return: the instance
        """
        return self._instance

    @property
    def solution(self) -> SolutionCore:
        """
        :return: the solution
        """
        return self._solution

    @solution.setter
    def solution(self, value: SolutionCore) -> None:
        self._solution = value

    @abstractmethod
    def solve(self, options: dict) -> dict:
        """
        Mandatory method

        :param options: configuration for solving the problem
        :return: a dictionary with status codes and other information

        This method produces and stores a solution
        """
        pass

    @abstractmethod
    def get_objective(self) -> float:
        """
        Mandatory method

        :return: the value of the current solution, represented by a number
        """
        pass

    def data_checks(self) -> dict:
        """
        Method that executes the ExperimentCore.check() method and validates the result against the schema_checks
        """
        try:
            checks = self.check()
            if checks is None:
                checks = self.check_solution()
        except NotImplementedError:
            # Add a deprecation warning here
            warnings.warn(
                "The check_solution() method is deprecated. Please use check() instead. "
                "Support for check_solution() will be removed on cornflow-client 2.0.0",
                DeprecationWarning,
            )
            checks = self.check_solution()
        validator = Draft7Validator(self.schema_checks)
        if not validator.is_valid(checks):
            raise BadSolutionChecks(
                f"The solution checks do not match the schema: {[e for e in validator.iter_errors(checks)]}"
            )
        return checks

    # TODO: make this method abstract on cornflow-client 2.0.0
    def check(self) -> Dict[str, Dict]:
        """
        Mandatory method

        :return: a dictionary of dictionaries. Each dictionary represents one type of error. Each of the elements
          inside represents one error of that particular type.
        """
        pass

    def check_solution(self) -> dict:
        """
        Mandatory method

        :return: a dictionary of dictionaries. Each dictionary represents one type of error. Each of the elements
          inside represents one error of that particular type.
        """
        pass

    @property
    @abstractmethod
    def schema_checks(self) -> dict:
        """
        A dictionary representation of the json-schema for the dictionary returned by
            the method ExperimentCore.check_solution()
        """
        raise NotImplementedError()

    @staticmethod
    def get_solver_config(
        config, lib="pyomo", default_solver="cbc", remove_unknown=False
    ):
        """
        Format the configuration used to solve the problem.
        Solver configuration can either be directly in config using cornflow mapping name
           or in a config["solver_config"] using the solver names. Nothing is ever removed from solver_config.
        Example:
            config = {
                "solver":"milp.cbc",
                "time_limit":60,
                "rel_gap":0.1,
                "solver_config":{"heur":1, "pumpC":0}
            }

        :param config: dict config argument of the solver method
        :param lib: str library used to create the model (pulp or pyomo)
        :param default_solver: str default solver to use if none is present inf config.
        :param remove_unknown: bool. if True, the unknown parameters will be deleted. Otherwise, they will remain
            but will not be translated.
        :return: the solver name and the config dict.
        """
        mapping = PARAMETER_SOLVER_TRANSLATING_MAPPING
        solver = config.get("solver", "unknown")

        if "." in solver:
            solver = solver.split(".")[1]

        solver = SOLVER_CONVERTER.get(solver)

        if solver is None:
            print(
                "The solver doesn't correspond to any solver in the parameters mapping. "
                f"Default solver {default_solver} will be used."
            )
            solver = default_solver

        if remove_unknown:
            conf = {
                mapping[k, lib, solver]: v
                for k, v in config.items()
                if (k, lib, solver) in mapping
            }
            if config.get("solver_config"):
                conf.update(
                    {
                        mapping.get((k, lib, solver), k): v
                        for k, v in config["solver_config"].items()
                    }
                )
        else:
            conf = {mapping.get((k, lib, solver), k): v for k, v in config.items()}
            conf.pop("solver", None)
            conf.pop("solver_config", None)
            if config.get("solver_config"):
                conf.update(
                    {
                        mapping.get((k, lib, solver), k): v
                        for k, v in config["solver_config"].items()
                    }
                )

        return conf

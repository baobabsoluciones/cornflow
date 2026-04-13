"""
Base code for the experiment template.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Union, Tuple
import logging as log

from jsonschema import Draft7Validator

from cornflow_client.constants import (
    PARAMETER_SOLVER_TRANSLATING_MAPPING,
    SOLVER_CONVERTER,
    BadSolutionChecks,
    BadKPIs,
)
from .instance import InstanceCore
from .instance_solution import CheckCore
from .solution import SolutionCore


class ExperimentCore(CheckCore, ABC):
    """
    The solver template.
    """
    schema_kpis = {}

    def __init__(
        self,
        instance: InstanceCore,
        solution: Union[SolutionCore, None] = None,
    ):
        # instance is read-only
        self._instance = instance
        self.solution = solution
        self.kpis = None

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
        # Check method always exists since it is implemented in the ExperimentCore class
        checks = self.check()
        validator = Draft7Validator(self.schema_checks)
        if not validator.is_valid(checks):
            raise BadSolutionChecks(
                f"The solution checks do not match the schema: {[e for e in validator.iter_errors(checks)]}"
            )
        return checks

    def get_kpis(self) -> dict:
        """
        Method that generates KPIs for the solution and validates the result against the schema_kpis
        """
        # generate_kpis method always exists since it is implemented in the ExperimentCore class
        self.kpis = self.generate_kpis()
        export_kpis = self.kpis_to_dict()
        validator = Draft7Validator(self.schema_kpis)
        if not validator.is_valid(export_kpis):
            raise BadKPIs(
                f"The solution KPIs do not match the schema: {[e for e in validator.iter_errors(export_kpis)]}"
            )
        return export_kpis

    def kpis_checks(self) -> dict:
        """
        Method that checks the solution with the KPIs and validates the result against the schema_checks.
        """
        # Validate the solution with the KPIs
        kpis_checks = self.check_kpis()
        validator = Draft7Validator(self.schema_checks)
        if not validator.is_valid(kpis_checks):
            raise BadSolutionChecks(
                f"The kpis checks do not match the schema: {[e for e in validator.iter_errors(kpis_checks)]}"
            )
        return kpis_checks

    def check(self) -> Dict[str, Union[List, Dict]]:
        """
        Method that runs all the checks for the solution.

        This method can be overridden by the user to modify the behaviour of the checks
        if wanted.

        :return: a dictionary of dictionaries. Each dictionary represents one type of error. Each of the elements
          inside represents one error of that particular type.
        """
        return self.launch_all_checks()

    def check_solution(self) -> Dict[str, Union[List, Dict]]:
        """
        Method that runs all the checks for the solution.
        This method will be deprecated on cornflow-client version 2.0.0

        This method can be overridden by the user to modify the behaviour of the checks
        if wanted.

        :return: a dictionary of dictionaries. Each dictionary represents one type of
          error. Each of the elements inside represents one error of that particular
          type.
        """
        return self.launch_all_checks()

    @property
    @abstractmethod
    def schema_checks(self) -> dict:
        """
        A dictionary representation of the json-schema for the dictionary returned by
            the method ExperimentCore.check_solution()
        """
        raise NotImplementedError()

    def _get_kpis_generation_methods(self) -> list:
        """
        Finds all class methods starting with kpis_ and returns them in a list.

        :return: A list of KPIs methods.
        """
        return [
            m
            for m in dir(self)
            if m.startswith("kpis_")
            and callable(getattr(self, m))
            and m not in ["kpis_checks", "kpis_to_dict"]
        ]

    def generate_kpis(self) -> Dict[str, Union[List, Dict]]:
        """
        Method that generates KPIs for the solution. By default, launches all methods
        starting with kpis_ and returns the result in a dictionary.

        This method can be overridden by the user to modify the behaviour of the KPI generation
        if wanted.

        :return: a dictionary of lists of dictionaries. Each list represents a table of KPIs.
            Each of the elements inside represents one row of that particular table.
        """
        kpis = {}
        for method in self._get_kpis_generation_methods():
            try:
                kpis[method[5:]] = getattr(self, method)()
            except Exception:
                # If a check fails, add a generic error message
                kpis[method[5:]] = [
                    {
                        "error_type": "KPI generation error",
                        "error_message": "The generation of the KPI has failed, please contact support",
                    }
                ]
                log.warning(
                    f"The execution of the check {method} has failed, please contact support"
                )
        kpis = {k: v for k, v in kpis.items() if v is not None and len(v)}
        return kpis

    def check_kpis(self) -> dict:
        """
        Method that checks the solution with the KPIs. By default, it does not perform any check.
        This method can be overridden by the user to modify the behavior of the KPI checks
        if wanted.
        :return: a dictionary of lists of dictionaries. Each list represents a table of KPI checks.
        Each of the elements inside represents one row of that particular table.
        """
        return {}

    def kpis_to_dict(self) -> dict:
        """
        Method that transforms the KPIs generated in self.kpis into a dictionary. By default, it returns self.kpis.
        This method can be overridden by the user to modify the behavior of the KPI transformation
        if wanted.
        :return: a dictionary with the KPIs. The format of the dictionary should be validated against self.schema_kpis
        """
        return self.kpis

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

        # Map the parameters in config to the solver and library. Parameters in solver_config are not mapped.
        if remove_unknown:
            # If remove_unknown is True, remove the unknown parameters from the config. Parameters in solver_config are not removed.
            conf = {
                mapping[k, lib, solver]: v
                for k, v in config.items()
                if (k, lib, solver) in mapping
            }
        else:
            conf = {mapping.get((k, lib, solver), k): v for k, v in config.items()}
            conf.pop("solver", None)
            conf.pop("solver_config", None)

        # Map the parameters in solver_config to the solver and library
        if config.get("solver_config"):
            conf.update(
                {
                    mapping.get((k, lib, solver), k): v
                    for k, v in config["solver_config"].items()
                }
            )

        return conf

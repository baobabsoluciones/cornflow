"""

"""

from abc import ABC, abstractmethod
from typing import Union, Dict
import json, tempfile
import os

from cornflow_client.constants import (
    PARAMETER_SOLVER_TRANSLATING_MAPPING,
    SOLVER_CONVERTER,
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

    @abstractmethod
    def check_solution(self, *args, **kwargs) -> Dict[str, Dict]:
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
           or in a config["solver_config"] using the solver names.
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
                        mapping[k, lib, solver]: v
                        for k, v in config["solver_config"].items()
                        if (k, lib, solver) in mapping
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

    def generate_report(self, report_name="report") -> str:
        """
        this method should write a report file, using the template in report_name.
        It returns the path to the file

        :param report_path: the path of the report to export
        :param report_name: the name of the template for the report
        """
        raise NotImplementedError()

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            InstanceCore.from_dict(data["instance"]),
            SolutionCore.from_dict(data["solution"]),
        )

    def to_dict(self) -> dict:
        return dict(instance=self.instance.to_dict(), solution=self.solution.to_dict())

    @classmethod
    def from_json(cls, path: str) -> "ExperimentCore":
        with open(path, "r") as f:
            data_json = json.load(f)
        return cls.from_dict(data_json)

    def to_json(self, path: str) -> None:
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)

    def generate_report_quarto(self, quarto, report_name: str = "report") -> str:
        # it returns the path to the file being written

        # a user may give the full "report.qmd" name.
        # We want to take out the extension
        path_without_ext = os.path.splitext(report_name)[0]

        path_to_qmd = path_without_ext + ".qmd"
        if not os.path.exists(path_to_qmd):
            raise FileNotFoundError(f"Report with path {path_to_qmd} does not exist.")
        path_to_output = path_without_ext + ".html"
        try:
            os.remove(path_to_output)
        except FileNotFoundError:
            pass
        try:
            quarto.quarto.find_quarto()
        except FileNotFoundError:
            raise ModuleNotFoundError("Quarto is not installed.")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "experiment.json")
            # write a json with instance and solution to temp file
            self.to_json(path)
            # pass the path to the report to render
            # it generates a report with path = path_to_output
            quarto.render(input=path_to_qmd, execute_params=dict(file_name=path))
        # quarto always writes the report in the .qmd directory.
        # thus, we need to return it so the user can move it if needed
        return path_to_output

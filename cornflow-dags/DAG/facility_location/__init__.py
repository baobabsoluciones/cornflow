from cornflow_client import ApplicationCore, get_empty_schema
from .core import Instance, Solution, Experiment
from cornflow_client.core.tools import load_json
from .solvers import PyomoSolver
from typing import Union, Type
import os


class FacilityLocation(ApplicationCore):
    name = "facility_location"
    instance = Instance
    solution = Solution
    solvers = dict(Pyomo=PyomoSolver)
    schema = load_json(os.path.join(os.path.dirname(__file__), "./schemas/config.json"))

    def get_solver(self, name: str = "Pyomo") -> Union[Type[Experiment], None]:
        if "." in name:
            solver, _ = name.split(".")
        else:
            solver = name
        return self.solvers.get(solver)

    @property
    def test_cases(self):
        data = load_json(
            os.path.join(os.path.dirname(__file__), "data/input_data_test1.json")
        )
        return [data]

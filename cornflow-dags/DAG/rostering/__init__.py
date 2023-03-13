"""

"""
# Imports from libraries
import os
from typing import Dict, List, Tuple, Union

# Imports from cornflow libraries
from cornflow_client import ApplicationCore
from cornflow_client.core.tools import load_json

# Imports from internal modules
from .core import Experiment, Instance, Solution
from .solvers import MipModel


class Rostering(ApplicationCore):
    name = "rostering"
    description = "Rostering model"
    instance = Instance
    solution = Solution
    solvers = dict(mip=MipModel)
    schema = load_json(os.path.join(os.path.dirname(__file__), "./schemas/config.json"))

    @property
    def test_cases(self) -> List[Union[Dict, Tuple[Dict, Dict]]]:
        data1 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_1.json")
        )
        data_out1 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_solution_1.json")
        )

        data_2 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_2.json")
        )

        data3 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_3.json")
        )
        data_out3 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_solution_3.json")
        )

        data_7 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_7.json")
        )

        return [(data1, data_out1), data_2, (data3, data_out3), data_7]

    def get_solver(self, name: str = "mip"):
        if "." in name:
            solver, _ = name.split(".")
        else:
            solver = name
        return self.solvers.get(solver)

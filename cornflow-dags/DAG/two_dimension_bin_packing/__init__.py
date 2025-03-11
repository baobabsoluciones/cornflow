import os
from typing import List, Dict

from cornflow_client import ApplicationCore
from cornflow_client.core.tools import load_json
from .core import Solution, Instance
from .solvers import RightCornerModel


class TwoDimensionBinPackingProblem(ApplicationCore):
    name = "two-dimension-bin-packing"
    description = "Problem for the two dimension bin packing problem."
    instance = Instance
    solution = Solution
    solvers = dict(right_corner=RightCornerModel)
    schema = load_json(os.path.join(os.path.dirname(__file__), "./schemas/config.json"))

    @property
    def test_cases(self) -> List[Dict]:
        data1 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_1.json")
        )
        data2 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_2.json")
        )

        return [
            # {
            #     "name": "example_1",
            #     "instance": data1,
            #     "description": "Example with 31 objects",
            # },
            {
                "name": "example_2",
                "instance": data2,
                "description": "Example with 25 objects",
            },
        ]

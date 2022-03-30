from cornflow_client import (
    ApplicationCore,
)
from cornflow_client.core.tools import load_json
from typing import List, Dict
import os

from .solvers import TSPNaive, ACOpy, OrToolsCP
from .core import Instance, Solution


class TspApp(ApplicationCore):
    name = "tsp"
    instance = Instance
    solution = Solution
    solvers = dict(naive=TSPNaive, aco=ACOpy, cpsat=OrToolsCP)
    schema = load_json(os.path.join(os.path.dirname(__file__), "schemas/config.json"))

    @property
    def test_cases(self) -> List[Dict]:
        instance = Instance.from_tsplib_file(
            os.path.join(os.path.dirname(__file__), "data/gr17.tsp")
        )
        return [instance.to_dict()]

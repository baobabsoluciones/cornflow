from cornflow_client import get_empty_schema, ApplicationCore
from .solvers import Algorithm, ORT_Algorithm, Heuristic, modelMIP
from .core import Solution, Instance
from cornflow_client.core.tools import load_json
import os
from typing import List, Dict


class VRP(ApplicationCore):
    name = "vrp"
    instance = Instance
    solution = Solution
    solvers = dict(
        algorithm1=Algorithm,
        algorithm2=Heuristic,
        algorithm3=ORT_Algorithm,
        mip=modelMIP,
    )
    schema = get_empty_schema(
        properties=dict(timeLimit=dict(type="number")), solvers=list(solvers.keys())
    )

    @property
    def test_cases(self) -> List[Dict]:
        data = load_json(
            os.path.join(os.path.dirname(__file__), "data/input_test_1_small.json")
        )
        return [data]

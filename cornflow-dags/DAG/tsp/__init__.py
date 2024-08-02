from cornflow_client import (
    ApplicationCore,
)
from cornflow_client.core.tools import load_json
from cornflow_client.schema.tools import add_reports_to_schema
from typing import List, Dict
import os

from .solvers import TSPNaive, OrToolsCP
from .core import Instance, Solution


class TspApp(ApplicationCore):
    name = "tsp"
    instance = Instance
    solution = Solution
    solvers = dict(naive=TSPNaive, cpsat=OrToolsCP)
    schema = load_json(os.path.join(os.path.dirname(__file__), "schemas/config.json"))
    schema["properties"]["solver"]["enum"] = list(solvers.keys())
    schema = add_reports_to_schema(schema, ["report"])

    @property
    def test_cases(self) -> List[Dict]:
        instance = Instance.from_tsplib_file(
            os.path.join(os.path.dirname(__file__), "data/gr17.tsp")
        )

        return [
            {
                "name": "Groetschel 17-city problem",
                "instance": instance.to_dict(),
                "description": "Example with 17 cities (Groetschel)",
            }
        ]

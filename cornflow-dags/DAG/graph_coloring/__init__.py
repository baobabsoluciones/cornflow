from cornflow_client import (
    get_empty_schema,
    ApplicationCore,
)
from typing import List, Dict
import pytups as pt
import os

from .solvers import OrToolsCP
from .core import Instance, Solution


class GraphColoring(ApplicationCore):
    name = "graph_coloring"
    instance = Instance
    solution = Solution
    solvers = dict(default=OrToolsCP)
    schema = get_empty_schema(
        properties=dict(timeLimit=dict(type="number")), solvers=list(solvers.keys())
    )
    reports = ["report"]
    schema["properties"]["report"] = dict(
        type="string", default=reports[0], enum=reports
    )

    @property
    def test_cases(self) -> List[Dict]:

        file_dir = os.path.join(os.path.dirname(__file__), "data")
        get_file = lambda name: os.path.join(file_dir, name)
        return [
            {
                "name": "gc_4_1",
                "instance": Instance.from_txt_file(get_file("gc_4_1")).to_dict(),
                "description": "Example data with 4 pairs",
            },
            {
                "name": "gc_50_1",
                "instance": Instance.from_txt_file(get_file("gc_50_1")).to_dict(),
                "description": "Example data with 50 pairs",
            },
        ]

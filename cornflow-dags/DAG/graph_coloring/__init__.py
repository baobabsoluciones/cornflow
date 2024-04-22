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

    @property
    def test_cases(self) -> List[Dict]:
        def read_file(filePath):
            with open(filePath, "r") as f:
                contents = f.read().splitlines()

            pairs = (
                pt.TupList(contents[1:])
                .vapply(lambda v: v.split(" "))
                .vapply(lambda v: dict(n1=int(v[0]), n2=int(v[1])))
            )
            return dict(pairs=pairs)

        file_dir = os.path.join(os.path.dirname(__file__), "data")

        return [
            {
                "name": "gc_4_1",
                "instance": read_file(os.path.join(file_dir, "gc_4_1")),
                "description": "Example data with 4 pairs",
            },
            {
                "name": "gc_50_1",
                "instance": read_file(os.path.join(file_dir, "gc_50_1")),
                "description": "Example data with 50 pairs",
            },
        ]

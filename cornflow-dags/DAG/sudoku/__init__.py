from cornflow_client import get_empty_schema, ApplicationCore, add_reports_to_schema
from typing import List, Dict
import os

from .solvers import OrToolsCP, Norvig
from .core import Instance, Solution


class Sudoku(ApplicationCore):
    name = "sudoku"
    instance = Instance
    solution = Solution
    solvers = dict(cpsat=OrToolsCP, norvig=Norvig)
    schema = get_empty_schema(
        properties=dict(timeLimit=dict(type="number")), solvers=list(solvers.keys())
    )
    schema = add_reports_to_schema(schema, ["report"])

    @property
    def test_cases(self) -> List[Dict]:

        file_dir = os.path.join(os.path.dirname(__file__), "data")
        get_file = lambda name: os.path.join(file_dir, name)

        def get_dataset(number, prefix):
            return dict(
                name=f"{prefix}_{number}",
                instance=Instance.from_txt_file(
                    get_file(f"{prefix}.txt"), number
                ).to_dict(),
                descriptipn=f"{prefix} example # {number}",
            )

        return (
            [get_dataset(n, "easy") for n in range(50)]
            + [get_dataset(n, "hardest") for n in range(11)]
            + [
                dict(
                    name="example_1",
                    instance=Instance.from_txt_file(get_file("example_1")).to_dict(),
                    descriptipn="Example 1",
                ),
                dict(
                    name="example_2",
                    instance=Instance.from_txt_file(get_file("example_2")).to_dict(),
                    descriptipn="Example 2",
                ),
            ]
        )

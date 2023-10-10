# Imports from libraries
import os
from typing import List, Dict, Union, Tuple, Type

# Imports from cornflow libraries
from cornflow_client import ApplicationCore
from cornflow_client.core.tools import load_json

# Imports from internal modules
from .core import Instance, Solution, Experiment
from .solvers import MipModel, ColumnGeneration


class BarCutting(ApplicationCore):
    name = "bar_cutting"
    instance = Instance
    solution = Solution
    solvers = dict(mip=MipModel, CG=ColumnGeneration)
    schema = load_json(os.path.join(os.path.dirname(__file__), "./schemas/config.json"))

    @property
    def test_cases(self) -> List[Union[Dict, Tuple[Dict, Dict]]]:
        options_instance = ["data/example_instance_1.json"]

        options_solution = ["data/example_solution_1.json"]

        return [
            (
                load_json(
                    os.path.join(
                        os.path.dirname(__file__),
                        options_instance[i],
                    )
                ),
                load_json(
                    os.path.join(
                        os.path.dirname(__file__),
                        options_solution[i],
                    )
                ),
            )
            for i in range(len(options_instance))
        ]

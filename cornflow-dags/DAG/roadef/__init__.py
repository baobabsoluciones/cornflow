from cornflow_client import ApplicationCore
from cornflow_client.core.tools import load_json
import os
from .core import Instance, Solution
from .solvers import Greedy, MIPModel, PeriodicMIP
from pytups import TupList


class Roadef(ApplicationCore):
    name = "roadef"
    instance = Instance
    solution = Solution
    schema = load_json(os.path.join(os.path.dirname(__file__), "./schemas/config.json"))
    solvers = dict(Greedy=Greedy, MIPModel=MIPModel, PeriodicMIPModel=PeriodicMIP)

    @property
    def test_cases(self):
        cwd = os.path.dirname(os.path.realpath(__file__))
        _get_file = lambda name: os.path.join(cwd, "data", name)
        _get_instance = lambda fn: Instance.from_json(_get_file(fn)).to_dict()
        _get_solution = lambda fn: Solution.from_json(_get_file(fn)).to_dict()

        return {
            "example": {
                "instance": _get_instance("example_instance_filtered.json"),
                "solution": _get_solution("example_solution_filtered.json"),
                "description": "Example data",
            }
        }

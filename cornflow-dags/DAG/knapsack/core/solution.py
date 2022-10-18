import pickle
from cornflow_client import SolutionCore
from cornflow_client.core.tools import load_json
import os


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution.json")
    )

    def copy(self):
        return Solution(pickle.loads(pickle.dumps(self.data, -1)))

    def get_ids(self):
        return [el["id"] for el in self.data["include"]]

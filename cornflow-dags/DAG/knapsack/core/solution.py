import pickle
from ..schemas import solution_schema
from cornflow_client import SolutionCore


class Solution(SolutionCore):
    schema = solution_schema

    def copy(self):
        return Solution(pickle.loads(pickle.dumps(self.data, -1)))

    def get_ids(self):
        return [el["id"] for el in self.data["include"]]

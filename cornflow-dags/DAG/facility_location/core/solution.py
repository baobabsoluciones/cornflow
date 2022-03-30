import json
import pickle
import os
from cornflow_client.core.tools import load_json
from cornflow_client import SolutionCore
from pytups import TupList


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution.json")
    )

    def to_json(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f)

    def copy(self):
        return Solution(pickle.loads(pickle.dumps(self.data, -1)))

    def get_solution_dict(self):
        return self.data["flows"]

    def get_pair_of_nodes_flows(self):
        return {(v["origin"], v["destination"]): v["flow"] for v in self.data["flows"]}

    def get_used_nodes(self):
        return TupList(
            [v["origin"] for v in self.data["flows"]]
            + [v["destination"] for v in self.data["flows"]]
        ).unique()

    def get_amount_supplied(self):
        return (
            TupList(
                {"origin": v["origin"], "product": v["product"], "flow": v["flow"]}
                for v in self.data["flows"]
            )
            .to_dict(result_col="flow", indices=["origin", "product"])
            .vapply(lambda v: sum(v))
        )

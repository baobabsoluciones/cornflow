import os
from cornflow_client import SolutionCore
from cornflow_client.core.tools import load_json
import pytups as pt


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/output.json")
    )

    def get_assignments(self):
        return pt.SuperDict({v["node"]: v["color"] for v in self.data["assignment"]})

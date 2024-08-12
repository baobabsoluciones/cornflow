import os
from cornflow_client import SolutionCore
from cornflow_client.core.tools import load_json
from ..core.tools import add_pos_square
import pytups as pt


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/output.json")
    )

    def __init__(self, data: dict):
        data = pt.SuperDict(data)
        data["assignment"] = pt.TupList(data["assignment"])
        super().__init__(data)

    def get_assignments(self, size):
        return add_pos_square(self.data["assignment"], size)

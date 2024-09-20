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
        properties = self.schema["properties"]
        for key in data:
            if properties[key]["type"] == "array":
                data[key] = pt.TupList(data[key])
            else:
                # if properties[key]['type'] == 'object':
                data[key] = pt.SuperDict(data[key])
        super().__init__(data)

    def get_assignments(self, size):
        return add_pos_square(self.data["assignment"], size)

    def get_others(self, size, id=None):
        if "alternatives" in self.data:
            if id is None:
                return add_pos_square(self.data["alternatives"], size)
            else:
                alternative = self.data["alternatives"].vfilter(lambda v: v["id"] == id)
                return add_pos_square(alternative, size)
        else:
            return pt.TupList()

    def get_indicators(self):
        return self.data.get("indicators", pt.SuperDict())

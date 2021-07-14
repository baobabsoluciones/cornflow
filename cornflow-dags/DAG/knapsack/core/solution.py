import pytups as pt
import json


class Solution:
    def __init__(self, data):
        self.data = pt.SuperDict.from_dict(data)

    def to_dict(self):
        return dict(self.data)

    def to_json(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f)

    def copy(self):
        return Solution(json.loads(json.dumps(self.data)))

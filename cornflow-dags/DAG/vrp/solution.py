import pytups as pt
import json
from .tools import load_json


class Solution(object):
    def __init__(self, data):
        # {route1: [n1, n2, n3], route2: [n4, n5, n6]}
        self.data = pt.SuperDict.from_dict(data)
        return

    def to_dict(self):
        routes = pt.SuperDict()
        for k, v in self.data["routes"].items():
            routes[k] = pt.TupList(v).kvapply(lambda k, v: (k, v))
        routes = routes.to_tuplist().vapply(
            lambda v: dict(route=v[0], pos=v[1], node=v[2])
        )
        return pt.SuperDict(routes=routes)

    @classmethod
    def from_dict(cls, data):
        datap = data
        return cls(datap)

    @classmethod
    def from_json(cls, path):
        with open(path, "r") as f:
            data_json = json.load(f)
        return cls.from_dict(data_json)

    def to_json(self, path):
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)

    @staticmethod
    def get_schema():
        return load_json("output.json")

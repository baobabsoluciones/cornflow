import pytups as pt
import json
from .tools import load_json


class Instance(object):
    def __init__(self, data):
        self.data = pt.SuperDict.from_dict(data)

    @classmethod
    def from_dict(cls, data):
        demand = pt.SuperDict({v["n"]: v for v in data["demand"]})

        weights = (
            pt.TupList(data["arcs"])
            .vapply(lambda v: v.values())
            .vapply(list)
            .to_dict(result_col=2, is_list=False)
        )
        datap = {**data, **dict(demand=demand, arcs=weights)}
        return cls(datap)

    def to_dict(self):
        raise NotImplementedError()

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
        return load_json("input.json")

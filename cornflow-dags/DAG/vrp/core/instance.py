import os
import pickle

import pytups as pt
from cornflow_client import InstanceCore, get_empty_schema
from cornflow_client.core.tools import load_json
from pytups import SuperDict


class Instance(InstanceCore):
    schema = load_json(os.path.join(os.path.dirname(__file__), "../schemas/input.json"))
    schema_checks = get_empty_schema()

    @classmethod
    def from_dict(cls, data) -> "Instance":
        demand = pt.SuperDict({v["n"]: v for v in data["demand"]})

        weights = (
            pt.TupList(data["arcs"])
            .vapply(lambda v: v.values())
            .vapply(lambda x: list(x))
            .to_dict(result_col=2, is_list=False)
        )
        datap = {**data, **dict(demand=demand, arcs=weights)}
        return cls(datap)

    def to_dict(self):
        data = pickle.loads(pickle.dumps(self.data, -1))
        data["demand"] = data["demand"].values_l()
        data["arcs"] = (
            data["arcs"].kvapply(lambda k, v: dict(n1=k[0], n2=k[1], w=v)).values_l()
        )

        return data

    def get_nodes(self):
        return [i["n"] for i in self.data["demand"].values()]

    def get_arcs(self):
        return self.data["arcs"].keys_tl()

    def get_vehicles(self):
        if self.data["parameters"]["numVehicles"] < 1:
            return list(range(self.data["parameters"]["size"]))
        return list(range(self.data["parameters"]["numVehicles"]))

    def get_weights(self):
        return self.data["arcs"]

    def _get_property(self, key, prop) -> SuperDict:
        return self.data[key].get_property(prop)

    def get_demand(self):
        return self._get_property("demand", "demand")

    def get_capacity(self):
        return {None: self.data["parameters"]["capacity"]}

    def get_depots(self):
        return [n["n"] for n in self.data["depots"]]

    def get_num_nodes(self):
        return self.data["parameters"]["size"]

    def get_num_vehicles(self):
        if self.data["parameters"]["numVehicles"] < 1:
            return self.data["parameters"]["size"]
        return self.data["parameters"]["numVehicles"]

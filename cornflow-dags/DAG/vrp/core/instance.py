import pytups as pt
from cornflow_client.core.tools import load_json
from cornflow_client import InstanceCore
import os
import pickle


class Instance(InstanceCore):
    schema = load_json(os.path.join(os.path.dirname(__file__), "../schemas/input.json"))

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

import pytups as pt
from cornflow_client.core.tools import load_json
from cornflow_client import SolutionCore
import os


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/output.json")
    )
    # {routes: {route1: [n1, n2, n3], route2: [n4, n5, n6]}}

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
        data_p = (
            data["routes"]
            .to_dict(result_col=["pos", "node"], indices=["route"])
            .vapply(lambda r: r.sorted(key=lambda t: t[0]).take(1))
        )
        return cls(pt.SuperDict(routes=data_p))

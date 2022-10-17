import os

import tsplib95 as tsp
from cornflow_client import InstanceCore, get_empty_schema
from cornflow_client.core.tools import load_json
from pytups import TupList, SuperDict


class Instance(InstanceCore):
    schema = load_json(os.path.join(os.path.dirname(__file__), "../schemas/input.json"))
    schema_checks = get_empty_schema()

    def __init__(self, data):
        data = SuperDict(data)
        data["arcs"] = TupList(data["arcs"])
        super().__init__(data)

    @classmethod
    def from_tsplib_file(cls, path):
        return cls.from_tsplib95(tsp.load(path))

    @classmethod
    def from_tsplib95(cls, problem):
        nodes = list(problem.get_nodes())
        edge_to_dict = lambda e: dict(
            n1=nodes[e[0]], n2=nodes[e[1]], w=problem.get_weight(*e)
        )
        arcs = TupList(edge_to_dict(e) for e in problem.get_edges())
        return cls(dict(arcs=arcs))

    def to_tsplib95(self):
        arcs = TupList(self.data["arcs"])
        nodes = (arcs.take("n1") + arcs.take("n2")).unique()
        pos = {k: v for v, k in enumerate(nodes)}
        arc_dict = arcs.to_dict(
            result_col="w", indices=["n1", "n2"], is_list=False
        ).to_dictdict()
        arc_weights = [[]] * len(nodes)
        for n1, n2dict in arc_dict.items():
            n1list = arc_weights[pos[n1]] = [0] * len(n2dict)
            for n2, w in n2dict.items():
                n1list[pos[n2]] = w

        if len(nodes) ** 2 == len(arcs):
            edge_weight_format = "FULL_MATRIX"
        elif abs(len(nodes) ** 2 - len(arcs) * 2) <= 2:
            edge_weight_format = "LOWER_DIAG_ROW"
        else:
            # TODO: can there another possibility?
            edge_weight_format = "LOWER_DIAG_ROW"
        dict_data = dict(
            name="TSP",
            type="TSP",
            comment="",
            dimension=len(nodes),
            edge_weight_type="EXPLICIT",
            edge_weight_format=edge_weight_format,
            edge_weights=arc_weights,
        )
        return tsp.models.StandardProblem(**dict_data)

    def get_arcs(self) -> TupList:
        return self.data["arcs"]

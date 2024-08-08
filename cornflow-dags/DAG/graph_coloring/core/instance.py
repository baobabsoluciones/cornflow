import os
from cornflow_client import InstanceCore, get_empty_schema
from cornflow_client.core.tools import load_json
import pytups as pt
import networkx as nx


class Instance(InstanceCore):
    schema = load_json(os.path.join(os.path.dirname(__file__), "../schemas/input.json"))
    schema_checks = get_empty_schema()

    def get_pairs(self):
        return pt.TupList(self.data["pairs"]).take(["n1", "n2"])

    def get_nodes(self):
        pairs = self.data["pairs"]
        n1s = pt.TupList(pairs).vapply(lambda v: v["n1"])
        n2s = pt.TupList(pairs).vapply(lambda v: v["n2"])
        return (n1s + n2s).unique2()

    @classmethod
    def from_txt_file(cls, filePath):
        with open(filePath, "r") as f:
            contents = f.read().splitlines()

        pairs = (
            pt.TupList(contents[1:])
            .vapply(lambda v: v.split(" "))
            .vapply(lambda v: dict(n1=int(v[0]), n2=int(v[1])))
        )
        return Instance.from_dict(dict(pairs=pairs))

    def get_graph(self):
        nodes = self.get_nodes()
        arcs = self.get_pairs()
        G = nx.Graph()
        for node in nodes:
            G.add_node(node)
        for n1, n2 in arcs:
            G.add_edge(n1, n2)
        return G

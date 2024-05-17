import os
from cornflow_client import SolutionCore
from cornflow_client.core.tools import load_json
import pytups as pt


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/output.json")
    )

    def get_route(self):
        return self.data["route"]

    def get_tour(self):
        return pt.TupList(self.get_route()).sorted(key=lambda v: v["pos"]).take("node")

    def get_used_arcs(self):
        tour = self.get_tour()

        if len(tour) <= 1:
            return []
        edges = pt.TupList(zip(tour, tour[1:]))
        edges.append((tour[-1], tour[0]))
        return edges

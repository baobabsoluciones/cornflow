from ..core import Experiment, Solution
from pytups import TupList
from cornflow_client.constants import SOLUTION_STATUS_FEASIBLE, STATUS_UNDEFINED


class TSPNaive(Experiment):
    def solve(self, options: dict):
        # we just get an arbitrary but complete list of nodes and we return it
        nodes = (
            TupList(v["n1"] for v in self.instance.get_arcs())
            .unique()
            .kvapply(lambda k, v: dict(pos=k, node=v))
        )
        self.solution = Solution(dict(route=nodes))
        return dict(status_sol=SOLUTION_STATUS_FEASIBLE, status=STATUS_UNDEFINED)

from ..core import Experiment, Solution
from pytups import TupList
import acopy as aco
from cornflow_client.constants import SOLUTION_STATUS_FEASIBLE, STATUS_UNDEFINED


class ACOpy(Experiment):
    def solve(self, options: dict):
        solver = aco.Solver(rho=options.get("rho", 0.03), q=options.get("q", 1))
        timeLimit_plugin = aco.plugins.TimeLimit(options.get("timeLimit", 10))
        solver.add_plugin(timeLimit_plugin)
        colony = aco.Colony(alpha=options.get("alpha", 1), beta=options.get("beta", 3))
        problem = self.instance.to_tsplib95()
        G = problem.get_graph()
        tour = solver.solve(G, colony, limit=100)
        solution = TupList(dict(pos=pos, node=el) for pos, el in enumerate(tour.nodes))
        self.solution = Solution(dict(route=solution))
        return dict(status_sol=SOLUTION_STATUS_FEASIBLE, status=STATUS_UNDEFINED)

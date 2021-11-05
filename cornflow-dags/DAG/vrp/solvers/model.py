from ..core import Experiment, Solution


class Algorithm(Experiment):
    def __init__(self, instance, solution=None):
        super().__init__(instance, solution)
        return

    def solve(self, options):
        route = 0
        input = self.instance.data
        solution = dict(routes={route: input["demand"].keys_l()})
        self.solution = Solution(solution)
        return dict(status=2)

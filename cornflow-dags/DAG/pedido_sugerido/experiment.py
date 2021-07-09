import pytups as pt
import os
from .instance import Instance
from .solution import Solution


class Experiment(object):
    def __init__(self, instance, solution):
        self.instance = instance
        if solution is None:
            solution = Solution(pt.SuperDict())
        self.solution = solution
        return

    def solve(self, options):
        raise NotImplementedError()

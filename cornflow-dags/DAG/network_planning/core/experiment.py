# Imports from libraries
from typing import Dict
from pytups import SuperDict, TupList
from gurobipy import GRB
import gurobipy as gp

# Imports from cornflow libraries
from cornflow_client import ExperimentCore

# Imports from internal modules
from .instance import Instance
from .solution import Solution


class Experiment(ExperimentCore):
    def __init__(self, instance, solution):
        if solution is None:
            solution = Solution(dict())
            super().__init__(instance, solution)

    @property
    def instance(self) -> Instance:
        return self._instance

    @property
    def solution(self) -> Solution:
        return self._solution

    @solution.setter
    def solution(self, value: Solution) -> None:
        self._solution = value

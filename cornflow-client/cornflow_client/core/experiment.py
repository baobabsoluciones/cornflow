from abc import ABC, abstractmethod
from .instance import InstanceCore
from .solution import SolutionCore
from typing import Union


class ExperimentCore(ABC):
    def __init__(
        self,
        instance: InstanceCore,
        solution: Union[SolutionCore, None] = None,
    ):
        # instance is read-only
        self._instance = instance
        self.solution = solution

    @property
    def instance(self) -> InstanceCore:
        return self._instance

    @property
    def solution(self) -> SolutionCore:
        return self._solution

    @solution.setter
    def solution(self, value: SolutionCore) -> None:
        self._solution = value

    @abstractmethod
    def solve(self, options: dict) -> dict:
        pass

    @abstractmethod
    def get_objective(self) -> float:
        pass

    @abstractmethod
    def check_solution(self, *args, **kwargs) -> dict:
        pass

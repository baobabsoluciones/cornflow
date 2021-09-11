from abc import ABC, abstractmethod
import json
from typing import List
from pytups import OrderSet, SuperDict


class InstanceSolutionCore(ABC):
    def __init__(self, data: dict):
        self.data = SuperDict.from_dict(data)

    @property
    def data(self) -> dict:
        return self._data

    @data.setter
    def data(self, value: dict):
        self._data = value

    @classmethod
    def from_dict(cls, data: dict) -> "MetaInstanceSolution":
        return cls(data)

    def to_dict(self) -> dict:
        return self.data

    @classmethod
    def from_json(cls, path: str) -> "MetaInstanceSolution":
        with open(path, "r") as f:
            data_json = json.load(f)
        return cls.from_dict(data_json)

    def to_json(self, path: str) -> None:
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)

    @property
    @abstractmethod
    def schema(self) -> dict:
        raise NotImplementedError()

    def new_set(self, seq: List):
        """
        Returns a new ordered set
        """
        return OrderSet(seq)

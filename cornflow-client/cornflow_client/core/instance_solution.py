from abc import ABC, abstractmethod
import json
from typing import List
from pytups import SuperDict
from jsonschema import Draft7Validator
from genson import SchemaBuilder


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
    def from_dict(cls, data: dict) -> "InstanceSolutionCore":
        return cls(data)

    def to_dict(self) -> dict:
        return self.data

    @classmethod
    def from_json(cls, path: str) -> "InstanceSolutionCore":
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

    def check_schema(self) -> List:
        validator = Draft7Validator(self.schema)
        data = self.to_dict()
        if not validator.is_valid(data):
            error_list = [e for e in validator.iter_errors(data)]
            return error_list
        return []

    def generate_schema(self) -> dict:
        builder = SchemaBuilder()
        builder.add_schema({"type": "object", "properties": {}})
        builder.add_object(self.to_dict())
        return builder.to_schema()

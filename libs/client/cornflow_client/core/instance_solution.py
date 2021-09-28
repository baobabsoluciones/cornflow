from abc import ABC, abstractmethod
import json
from typing import List
from pytups import SuperDict
from jsonschema import Draft7Validator
from genson import SchemaBuilder


class InstanceSolutionCore(ABC):
    """
    Common interface for the instance and solution templates
    """

    def __init__(self, data: dict):
        self.data = SuperDict.from_dict(data)

    @property
    def data(self) -> dict:
        """
        input data (not necessarily in json-format)
        """
        return self._data

    @data.setter
    def data(self, value: dict):
        self._data = value

    @classmethod
    def from_dict(cls, data: dict) -> "InstanceSolutionCore":
        """
        :param data: json-schema in a dictionary format

        :return: an object initialized from the dict json-schema
        """
        return cls(data)

    def to_dict(self) -> dict:
        """
        :return: a dictionary with the json-schema representation
        """
        return self.data

    @classmethod
    def from_json(cls, path: str) -> "InstanceSolutionCore":
        """
        :param path: path to json-schema json file

        :return: an object initialized from the json-schema formatted json file
        """
        with open(path, "r") as f:
            data_json = json.load(f)
        return cls.from_dict(data_json)

    def to_json(self, path: str) -> None:
        """
        :param path: path to json-schema json file

        writes a json file with the json-schema representation of the object
        """

        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)

    @property
    @abstractmethod
    def schema(self) -> dict:
        """
        a dictionary representation of the json-schema for the object
        """

        raise NotImplementedError()

    def check_schema(self) -> List:
        """
        checks that the json-schema export complies with the defined schema

        :return: a list of errors
        """

        validator = Draft7Validator(self.schema)
        data = self.to_dict()
        if not validator.is_valid(data):
            return [e for e in validator.iter_errors(data)]
        return []

    def generate_schema(self) -> dict:
        """
        :return: a dict json-schema based on the current data
        """
        builder = SchemaBuilder()
        builder.add_schema({"type": "object", "properties": {}})
        builder.add_object(self.to_dict())
        return builder.to_schema()

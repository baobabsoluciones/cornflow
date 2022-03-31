"""

"""
# Full imports
import json

# Partial imports
from abc import ABC, abstractmethod
from genson import SchemaBuilder
from jsonschema import Draft7Validator
from pytups import SuperDict
from typing import List

# Imports from internal modules
from .read_tools import read_excel, is_xl_type


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

    @classmethod
    def from_excel(cls, path: str) -> "InstanceSolutionCore":
        """
        Read an entire excel file.

        :param path: path of the excel file
        :return: a dict with a list of dict (records format) for each table.
        """

        param_tables_names = cls.__get_parameter_tables_names()

        tables = read_excel(path, param_tables_names)
        return cls.from_dict(tables)

    @classmethod
    def __get_parameter_tables_names(cls) -> List:
        """
        :return: The names of the table of the schema that are parameter tables
        """
        json_schema = cls(dict()).schema
        if json_schema.get("properties", None):
            return [
                table_name
                for table_name, content in json_schema["properties"].items()
                if content["type"] == "object"
            ]
        return []

    def to_excel(self, path: str):
        """
        Write data to excel.

        :param path: path or name of the excel file
        :return: nothing
        """
        try:
            import pandas as pd
        except (ImportError, ModuleNotFoundError):
            raise Exception("You must install pandas package to use this method")

        is_xl_type(path)

        data = self.to_dict()

        with pd.ExcelWriter(path) as writer:
            for table in data.keys():
                content = data[table]
                if isinstance(content, list):
                    pd.DataFrame.from_records(content).to_excel(
                        writer, table, index=False
                    )
                elif isinstance(content, dict):
                    pd.DataFrame.from_dict(content, orient="index").to_excel(
                        writer, table, header=False
                    )

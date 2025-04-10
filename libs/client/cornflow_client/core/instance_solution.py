""" """

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List

from genson import SchemaBuilder
from jsonschema import Draft7Validator
from pytups import SuperDict

from .read_tools import read_excel, is_xl_type

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


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

    def _get_property(self, key, prop) -> SuperDict:
        return self.data[key].get_property(prop)

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
        except ImportError:
            raise ImportError("You must install pandas package to use this method")

        is_xl_type(path)

        data = self.to_dict()

        with pd.ExcelWriter(path) as writer:
            for table in data.keys():
                content = data[table]
                if isinstance(content, list):
                    pd.DataFrame.from_records(content).to_excel(
                        writer, sheet_name=table, index=False
                    )
                elif isinstance(content, dict):
                    pd.DataFrame.from_dict(content, orient="index").to_excel(
                        writer, sheet_name=table, header=False
                    )

    """
    DATA HANDLING METHODS
    """

    @staticmethod
    def _try_convert_string(s):
        """Tries to convert a string to int or float."""
        if not isinstance(s, str):
            return s
        if s.isnumeric():
            return int(s)
        try:
            return float(s)
        except ValueError:
            return s

    @staticmethod
    def _convert_value(value):
        """Recursively converts values within lists and dicts."""
        if isinstance(value, str):
            return InstanceSolutionCore._try_convert_string(value)
        elif isinstance(value, list):
            # Recursively convert each item in the list
            return [InstanceSolutionCore._convert_value(item) for item in value]
        elif isinstance(value, dict):
            # Recursively convert each value in the dictionary
            return {k: InstanceSolutionCore._convert_value(v) for k, v in value.items()}
        else:
            # Return other types (int, float, bool, None, etc.) as is
            return value

    @staticmethod
    def dict_to_int_or_float(data_dict):
        """
        Recursively transforms a dictionary (and nested structures) by converting
        string representations of numbers into actual int or float types.
        Returns a new dictionary with converted values, does not modify the original.

        For example: Transforms {a: '4', b: {c: '7', d: ['8.7', '9']}}
            into {a: 4, b: {c: 7, d: [8.7, 9]}}
        """
        if not isinstance(data_dict, dict):
            # Consider raising TypeError if input must be a dict
            # Or return input if other types should pass through?
            # For now, mimicking potential pass-through if not dict.
            return data_dict

        # Start the recursive conversion using the helper
        return InstanceSolutionCore._convert_value(data_dict)

    @staticmethod
    def from_element_or_list_to_dict(element_or_list):
        """
        Converts a list into a dictionary indexed by the field 'index' of each element of the list.
        If the input is not a list, it is converted into a list before converting to a dictionary
        For example: [{'index': 4, 'value': 5}, {'index': 7, 'value': 8}]
            is transformed to {4: {'index': 4, 'value': 5}, 7: {'index': 7, 'value': 8}}
        """
        if not isinstance(element_or_list, list):
            element_or_list = [element_or_list]
        return {int(el["index"]): el for el in element_or_list}

    @staticmethod
    def get_date_from_string(string: str) -> datetime:
        """
        Returns a datetime object from an hour-string in format 'YYYY-MM-DD'
        """
        return datetime.strptime(string, "%Y-%m-%d")

    @staticmethod
    def get_datetime_from_string(string: str) -> datetime:
        """
        Returns a datetime object from an hour-string in format 'YYYY-MM-DDTh:m'
        """
        return datetime.strptime(string, "%Y-%m-%dT%H:%M")

    @staticmethod
    def get_datetimesec_from_string(string: str) -> datetime:
        """
        Returns a datetime object from an hour-string in format 'YYYY-MM-DDTh:m:s'
        """
        return datetime.strptime(string, DATETIME_FORMAT)

    @staticmethod
    def get_datetime_from_date_hour(date: str, hour: int) -> datetime:
        """
        Returns a datetime object from a date and an hour
        """
        if hour == 24:
            hour = 0
        return datetime.strptime(f"{date}T{hour}", "%Y-%m-%dT%H")

    @staticmethod
    def get_date_hour_from_string(string: str, zero_to_twenty_four=False):
        """
        Returns a tuple (date, hour) from an hour-string
        """
        date_t = datetime.strptime(string, DATETIME_FORMAT)
        hour = date_t.strftime("%H")
        if hour == "00" and zero_to_twenty_four:
            hour = "24"
            date_t -= timedelta(days=1)
        date = date_t.strftime("%Y-%m-%d")
        return date, int(hour)

    @staticmethod
    def get_date_string_from_ts(ts: datetime) -> str:
        """Returns the string of a given date as 'YYYY-MM-DD'"""
        return datetime.strftime(ts, "%Y-%m-%d")

    @staticmethod
    def get_datetime_string_from_ts(ts: datetime) -> str:
        """Returns the string of a given date as 'YYYY-MM-DDTh:m'"""
        return datetime.strftime(ts, "%Y-%m-%dT%H:%M")

    @staticmethod
    def get_datetimesec_string_from_ts(ts: datetime) -> str:
        """Returns the string of a given date as 'YYYY-MM-DDTh:m:s'"""
        return datetime.strftime(ts, DATETIME_FORMAT)

    @staticmethod
    def get_next_hour_datetime_string(string: str) -> str:
        """
        Returns the hour following the given hour, as a string
        """
        date_t = datetime.strptime(string, DATETIME_FORMAT)
        return (date_t + timedelta(hours=1)).isoformat()

    # Alias: get_next_hour_datetimesec_string points to the same implementation
    get_next_hour_datetimesec_string = get_next_hour_datetime_string

    @staticmethod
    def get_next_hour(ts: datetime) -> datetime:
        """
        Returns the hour following the given hour
        """
        return ts + timedelta(hours=1)

    @staticmethod
    def get_previous_hour_datetime_string(string: str) -> str:
        """
        Returns the hour preceding the given hour, as a string
        """
        date_t = datetime.strptime(string, DATETIME_FORMAT)
        return (date_t - timedelta(hours=1)).isoformat()

    @staticmethod
    def get_previous_hour_datetimesec_string(string: str) -> str:
        """
        Returns the hour preceding the given hour, as a string
        """
        date_t = datetime.strptime(string, "%Y-%m-%dT%H:%M:%S.%f")
        return (date_t - timedelta(hours=1)).isoformat()

    @staticmethod
    def get_previous_hour(ts: datetime) -> datetime:
        """
        Returns the hour preceding the given hour
        """
        return ts - timedelta(hours=1)

    @staticmethod
    def get_date_string_from_ts_string(ts: str) -> str:
        """Returns the date in format 'YYYY-MM-DD' from a datetime string"""
        return ts[0:10]

    @staticmethod
    def get_hour_from_ts(ts: datetime) -> float:
        """Returns the hours (in number) of the given time slot"""
        return float(ts.hour + ts.minute / 60)

    @staticmethod
    def add_time_to_ts(ts: datetime, weeks=0, days=0, minutes=0, seconds=0) -> datetime:
        """Adds time to a datetime"""
        return ts + timedelta(days=7 * weeks + days, minutes=minutes, seconds=seconds)

    @staticmethod
    def add_time_to_date_string(
        string: str, weeks=0, days=0, minutes=0, seconds=0
    ) -> str:
        """Adds time to a date string"""
        date = datetime.strptime(string, "%Y-%m-%d").date()
        return (
            date + timedelta(days=7 * weeks + days, minutes=minutes, seconds=seconds)
        ).strftime("%Y-%m-%d")

    @staticmethod
    def add_time_to_datetime_string(
        string: str, weeks=0, days=0, minutes=0, seconds=0
    ) -> str:
        """Adds time to a datetime"""
        datetime_object = datetime.strptime(string, DATETIME_FORMAT)
        return (
            datetime_object
            + timedelta(days=7 * weeks + days, minutes=minutes, seconds=seconds)
        ).strftime(DATETIME_FORMAT)

    @staticmethod
    def add_time_to_datetimesec_string(
        string: str, weeks=0, days=0, hours=0, minutes=0, seconds=0
    ) -> str:
        """Adds time to a datetime"""
        datetime_object = datetime.strptime(string, DATETIME_FORMAT)
        return (
            datetime_object
            + timedelta(
                weeks=weeks,
                days=7 * weeks + days,
                hours=hours,
                minutes=minutes,
                seconds=seconds,
            )
        ).strftime(DATETIME_FORMAT)

    @staticmethod
    def get_week_from_ts(ts: datetime) -> int:
        """Returns the integer value of the week for the given time slot"""
        return ts.isocalendar()[1]

    @staticmethod
    def get_week_from_date_string(string: str) -> int:
        """Returns the integer value of the week for the given string"""
        date_object = datetime.strptime(string, "%Y-%m-%d").date()
        return date_object.isocalendar()[1]

    @staticmethod
    def get_week_from_datetime_string(string: str) -> int:
        """Returns the integer value of the week for the given string"""
        datetime_object = datetime.strptime(string, "%Y-%m-%dT%H:%M")
        return datetime_object.isocalendar()[1]

    @staticmethod
    def get_week_from_datetimesec_string(string: str) -> int:
        """Returns the integer value of the week for the given string"""
        datetime_object = datetime.strptime(string, DATETIME_FORMAT)
        return datetime_object.isocalendar()[1]

    @staticmethod
    def get_weekday_from_ts(ts: datetime) -> int:
        """Returns the number of the weekday from a ts"""
        return ts.isocalendar()[2]

    @staticmethod
    def get_weekday_from_date_string(string: str) -> int:
        """Returns the number of the weekday from a date string in format 'YYYY-MM-DD'"""
        date = datetime.strptime(string, "%Y-%m-%d").date()
        return date.isocalendar()[2]

    @staticmethod
    def get_weekday_from_datetime_string(string: str) -> int:
        """Returns the number of the weekday from a date string in format 'YYYY-MM-DDTh:m'"""
        datetime_obj = datetime.strptime(string, DATETIME_FORMAT)
        return datetime_obj.isocalendar()[2]

    @staticmethod
    def get_weekday_from_datetimesec_string(string: str) -> int:
        """Returns the number of the weekday from a date string in format 'YYYY-MM-DDT:h:m:s'"""
        datetime_obj = datetime.strptime(string, DATETIME_FORMAT)
        return datetime_obj.isocalendar()[2]

    @staticmethod
    def get_hour_from_datetime_string(string: str) -> float:
        """Returns the integer value of the hour (in number) from ts string in format 'YYYY-MM-DDTh:m'"""
        datetime_obj = datetime.strptime(string, DATETIME_FORMAT)
        return datetime_obj.hour

    @staticmethod
    def get_hour_from_datetimesec_string(string: str) -> float:
        """Returns the integer value of the hour (in number) from ts string in format 'YYYY-MM-DDTh:m:s'"""
        datetime_obj = datetime.strptime(string, DATETIME_FORMAT)
        return datetime_obj.hour

"""
Class to help create and manage data schema and to validate json files.
"""
# Full imports
import os

# Partial imports
from copy import deepcopy
from genson import SchemaBuilder
from jsonschema import Draft7Validator


# Imports form internal modules
from .dictSchema import DictSchema
from cornflow_client.core.tools import load_json, save_json


class SchemaManager:
    """
    A schema manager between json-schema, dict-schema and marshmallow
    """

    def __init__(self, schema, validator=Draft7Validator):
        """
        Class to help create and manage data schema.
        Once a schema is loaded, allow the validation of data.

        :param schema: a json schema
        """
        self.validator = validator
        self.jsonschema = schema

    @classmethod
    def from_filepath(cls, path):
        """
        Load a json schema from a json file.

        :param path the file path

        return The SchemaManager instance
        """

        schema = cls.load_json(path)
        return cls(schema)

    def get_jsonschema(self):
        """
        Return a copy of the stored jsonschema.
        """
        return deepcopy(self.jsonschema)

    def get_validation_errors(self, data):
        """
        Validate json data according to the loaded jsonschema and return a list of errors.
        Return an empty list if data is valid.

        :param dict data: data to validate.

        :return: A list of validation errors.

        For more details about the error format, see:
        https://python-jsonschema.readthedocs.io/en/latest/errors/#jsonschema.exceptions.ValidationError
        """
        v = self.validator(self.get_jsonschema())

        if not v.is_valid(data):
            error_list = [e for e in v.iter_errors(data)]
            return error_list
        return []

    def validate_data(self, data, print_errors=False):
        """
        Validate json data according to the loaded jsonschema.

        :param dict data: the data to validate.
        :param bool print_errors: If true, will print the errors.

        :return: True if data format is valid, else False.
        """
        errors_list = self.get_validation_errors(data)

        if print_errors:
            for e in errors_list:
                print(e)

        return len(errors_list) == 0

    def validate_schema(self, print_errors=False):
        """
        Validate the loaded jsonschema
        :param bool print_errors: If true, will print the errors

        :return: True if jsonschema is valid, else False
        """
        path_schema_validator = os.path.join(
            os.path.dirname(__file__), "../data/schema_validator.json"
        )
        validation_schema = load_json(path_schema_validator)
        v = self.validator(validation_schema)

        if v.is_valid(self.get_jsonschema()):
            return True

        error_list = [e for e in v.iter_errors(self.get_jsonschema())]
        if print_errors:
            for e in error_list:
                print(e)
        return False

    def get_file_errors(self, path):
        """
        Get json file errors according to the loaded jsonschema.

        :param path the file path

        :return: A list of validation errors.
          For more details about the error format, see:
          https://python-jsonschema.readthedocs.io/en/latest/errors/#jsonschema.exceptions.ValidationError
        """
        data = self.load_json(path)
        return self.get_validation_errors(data)

    def validate_file(self, path, print_errors=False):
        """
        Validate a json file according to the loaded jsonschema.

        :param path the file path
        :param print_errors: If true, will print the errors.

        :return: True if the data is valid and False if it is not.
        """
        data = self.load_json(path)
        return self.validate_data(data, print_errors=print_errors)

    def to_dict_schema(self):
        """
        Transform a jsonschema into a dictionary format

        :return: The schema dictionary
        """

        return self.to_schema_dict_obj().get_schema()

    def to_schema_dict_obj(self):
        """
        Returns an DictSchema object equivalent of the jsonschema

        """
        return DictSchema(self.get_jsonschema())

    @property
    def schema_dict(self):
        return self.to_dict_schema()

    def to_marshmallow(self):
        """
        Create marshmallow schemas

        :return: a dict containing the flask marshmallow schemas
        :rtype: Schema()
        """
        return self.to_schema_dict_obj().to_marshmallow()

    def export_schema_dict(self, path):
        """
        Print the schema_dict in a json file.

        :param path: the path where to save the dict.format

        :return: nothing
        """
        self.save_json(self.to_dict_schema(), path)

    def draft_schema_from(self, path, save_path=None):
        """
        Create a draft jsonschema from a json file of data.

        :param path: path to the json file.
        :param save_path: path where to save the generated schema.

        :return: the generated schema.
        """
        file = self.load_json(path)

        builder = SchemaBuilder()
        builder.add_schema({"type": "object", "properties": {}})
        builder.add_object(file)

        draft_schema = builder.to_json()
        if save_path is not None:
            with open(save_path, "w") as outfile:
                outfile.write(draft_schema)
        return draft_schema

    def to_template(self):
        """

        This function assumes certain structure for the jsonschema.
        For now, three types of tables exist: array of objects, arrays and objects.
        {
        table1: [{col1: a, col2: b}, {col1: aa, col2: bb}, ...],
        table2: [1, 2, 3, ],
        table3: {config1: a, config2: b},
        }

        """
        master_table_name = "_README"
        type_table_name = "_TYPES"
        tables = {master_table_name: [], type_table_name: []}
        # we update the master table of tables:
        real_props = [
            (k, v)
            for (k, v) in self.jsonschema["properties"].items()
            if not k.startswith("$")
        ]
        for key, value in real_props:
            tables[master_table_name].append(
                dict(table=key, description=value.get("description", ""))
            )
        # then we get each table
        for key, value in real_props:
            tables[key] = self._get_table(value)
            # then we get column types
        example_inv = {1: "integer", "string": "string"}
        for key, value in real_props:
            rows = []
            if len(tables[key]) > 1:
                rows = [
                    dict(table=key, column=v, type="string") for v in ["key", "value"]
                ]
            if len(tables[key]) == 1:
                row1 = tables[key][0]
                rows = [
                    dict(table=key, column=k, type=example_inv[v])
                    for k, v in row1.items()
                ]
            tables[type_table_name].extend(rows)
        return tables

    @staticmethod
    def _get_table(contents):
        example = dict(integer=1, string="string")
        # several cases here:
        if contents["type"] == "object":
            # two columns: key-value in two columns
            properties = contents["properties"]
            return [
                dict(key=k, value=example[v["type"]]) for k, v in properties.items()
            ]
        # we're here, we're probably in an array
        assert contents["type"] == "array"
        items = contents["items"]
        if items["type"] != "object":
            # only one column with name
            return [example[items["type"]]]
        # here is a regular table:
        props = items["properties"]
        # if there are array of single values, we flatten them into one column:
        p_arrays = {
            k: v["items"]
            for k, v in props.items()
            if v["type"] == "array" and v["items"]["type"] != "object"
        }
        # if a column is an array of objects: we flatten the object into several columns
        p_arrays_objects = {
            "{}.{}".format(k, kk): vv["items"]
            for k, v in props.items()
            if v["type"] == "array" and v["items"]["type"] == "object"
            for kk, vv in v["items"]["properties"].items()
        }
        # the rest of columns stay the same
        p_no_array = {k: v for k, v in props.items() if v["type"] != "array"}
        props = {**p_arrays, **p_no_array, **p_arrays_objects}
        required = items["required"]
        rm_keys = props.keys() - set(required)
        # order is: first required in order, then the rest:
        one_line = {k: example[props[k]["type"]] for k in required}
        for k in rm_keys:
            one_line[k] = example[props[k]["type"]]
        return [one_line]

    @staticmethod
    def load_json(path):
        """
        Load a json file

        :param path: the path of the json file.json

        return the json content.
        """
        return load_json(path)

    @staticmethod
    def save_json(data, path):
        return save_json(data, path)

    """
    Aliases:
    """
    dict_to_flask = to_marshmallow
    load_schema = from_filepath
    jsonschema_to_flask = to_marshmallow
    jsonschema_to_dict = to_dict_schema

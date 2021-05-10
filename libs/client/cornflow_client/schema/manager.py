"""
Class to help create and manage data schema and to validate json files.
"""

import json
from jsonschema import Draft7Validator
from copy import deepcopy
from genson import SchemaBuilder
from .dictSchema import DictSchema


class SchemaManager:

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
            with open(save_path, 'w') as outfile:
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
        master_table_name = '_README'
        example = dict(integer=1, string="string")
        tables = {master_table_name: []}
        for key, value in self.jsonschema['properties'].items():
            if key.startswith("$"):
                continue
            description = value.get('description', "")
            # update the master table of tables:
            tables[master_table_name].append(dict(name=key, description=description))
            # several cases here:
            if value['type'] == 'object':
                # two columns: key-value in two columns
                properties = value['properties']
                tables[key] = [dict(key=k, value=example[v['type']]) for k, v in properties.items()]
                continue
            # we're here, we're probably in an array
            assert value['type'] == 'array'
            items = value['items']
            if items['type'] != 'object':
                # only one column with name
                tables[key] = [example[items['type']]]
                continue
            # here is a regular table:
            props = items['properties']
            # if there are array of single values, we flatten them into one column:
            p_arrays = {k: v['items'] for k, v in props.items()
                        if v['type']=='array' and v['items']['type'] != 'object'}
            # if a column is an array of objects: we flatten the object into several columns
            p_arrays_objects = {'{}.{}'.format(k, kk): vv['items'] for k, v in props.items()
                                if v['type'] == 'array' and v['items']['type'] == 'object'
                                for kk, vv in v['items']['properties'].items()
                                }
            # the rest of columns stay the same
            p_no_array = {k: v for k, v in props.items() if v['type'] != 'array'}
            props = {**p_arrays, **p_no_array, **p_arrays_objects}
            required = items['required']
            rm_keys = props.keys() - set(required)
            # order is: first required in order, then the rest:
            one_line = {k: example[props[k]['type']] for k in required}
            for k in rm_keys:
                one_line[k] = example[props[k]['type']]
            tables[key] = [one_line]
        return tables

    @staticmethod
    def load_json(path):
        """
        Load a json file

        :param path: the path of the json file.json

        return the json content.
        """
        with open(path) as json_file:
            file = json.load(json_file)
        return file

    @staticmethod
    def save_json(data, path):
        with open(path, 'w') as outfile:
            json.dump(data, outfile)

    """
    Aliases:
    """
    dict_to_flask = to_marshmallow
    load_schema = from_filepath
    jsonschema_to_flask = to_marshmallow
    jsonschema_to_dict = to_dict_schema

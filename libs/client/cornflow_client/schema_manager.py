"""
Class to help create and manage data schema and to validate json files.
"""

import json
import re
from jsonschema import Draft7Validator
from copy import deepcopy
from genson import SchemaBuilder
from .schema_dict_functions import gen_schema, ParameterSchema, sort_dict
from .constants import JSON_TYPES, DATASCHEMA


class SchemaManager:
    
    def __init__(self, schema=None):
        """
        Class to help create and manage data schema.
        Once a schema is loaded, allow the validation of data.
        
        :param schema: a json schema
        """
        self.default_validator = Draft7Validator
        self.jsonschema = schema if schema is not None else {}
        self.types = JSON_TYPES
        self.schema_dict = self.get_empty_schema()
    
    def get_empty_schema(self):
        """
        Create un empty schema dict
        """
        return {DATASCHEMA: []}
    
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
    
    def is_schema_loaded(self):
        """
        Check if a schema is loaded.
        """
        loaded = len(self.jsonschema) > 0
        if not loaded:
            raise Warning("No jsonschema has been loaded in the SchemaManager class")
        return loaded
    
    def get_validation_errors(self, data, validator=None):
        """
        Validate json data according to the loaded jsonschema and return a list of errors.
        Return an empty list if data is valid.

        :param dict data: data to validate.
        :param validator: A jsonschema IValidator class. If None, will use self.default_validator.

        :return: A list of validation errors.

        For more details about the error format, see:
        https://python-jsonschema.readthedocs.io/en/latest/errors/#jsonschema.exceptions.ValidationError
        """
        self.is_schema_loaded()
    
        if validator is None:
            validator = self.default_validator
        v = validator(self.get_jsonschema())

        if not v.is_valid(data):
            error_list = [e for e in v.iter_errors(data)]
            return error_list
        return []
    
    def validate_data(self, data, validator=None, print_errors=False):
        """
        Validate json data according to the loaded jsonschema.

        :param dict data: the data to validate.
        :param validator: A jsonschema IValidator class. If None, will use self.default_validator.
        :param bool print_errors: If true, will print the errors.

        :return: True if data format is valid, else False.
        """
        errors_list = self.get_validation_errors(data, validator=validator)
        
        if print_errors:
            for e in errors_list:
                print(e)
        
        return len(errors_list) == 0
    
    def get_file_errors(self, path, validator=None):
        """
        Get json file errors according to the loaded jsonschema.

        :param path the file path
        :param validator A jsonschema IValidator class. If None, will use self.default_validator.

        :return: A list of validation errors.
        For more details about the error format, see:
        https://python-jsonschema.readthedocs.io/en/latest/errors/#jsonschema.exceptions.ValidationError
        """
        data = self.load_json(path)
        return self.get_validation_errors(data, validator=validator)
    
    def validate_file(self, path, validator=None, print_errors=False):
        """
        Validate a json file according to the loaded jsonschema.
        
        :param path the file path
        :param validator A jsonschema IValidator class. If None, will use self.default_validator.
        :param print_errors: If true, will print the errors.
        
        :return: True if the data is valid and False if it is not.
        """
        data = self.load_json(path)
        return self.validate_data(data, validator=validator, print_errors=print_errors)
    
    def jsonschema_to_dict(self):
        """
        Transform a jsonschema into a dictionary and store it in self.schema_dict
        
        :return: The schema dictionary
        """ 
        jsonschema = self.get_jsonschema()
        
        if not self.is_schema_loaded():
            return self.schema_dict
        
        self.schema_dict = self.get_empty_schema()

        # if jsonschema["type"] == 'array':
        #     item = "Object", jsonschema["items"]
        #     self._get_element_dict(item)
        #     item2 = "Object", jsonschema
        #     self._create_data_schema(item2)
        #     return self.schema_dict

        if "definitions" in jsonschema:
            for item in jsonschema["definitions"].items():
                self._get_element_dict(item)

        if "properties" in jsonschema:
            for item in jsonschema["properties"].items():
                self._get_element_dict(item)
                self._create_data_schema(item)

        return self.schema_dict

    def dict_to_flask(self):
        """
        Create flask marshmallow schemas from self.dict_schema
        
        :return: a dict containing the flask marshmallow schemas
        :rtype: Schema()
        """
        dict_params = self.schema_dict
        result_dict = {}
        ordered = sort_dict(dict_params)
        tuplist = sorted(dict_params.items(), key=lambda v: ordered[v[0]])
        for key, params in tuplist:
            schema = ParameterSchema()
            # this line validates the list of parameters:
            params1 = schema.load(params, many=True)
            result_dict[key] = gen_schema(key, params1, result_dict)
        
        return result_dict[DATASCHEMA]
    
    def jsonschema_to_flask(self):
        """
        Create marshmallow schemas from the jsonschema

        :return: a dict containing the marshmallow schema
        """
        self.jsonschema_to_dict()
        return self.dict_to_flask()
        
    def load_schema(self, path):
        """
        Load a json schema into self.jsonschema.

        :param path: the path to the json file containing the schema.json

        return the jsonschema
        """
        self.jsonschema = self.load_json(path)
        self.schema_dict = self.get_empty_schema()
        return self.jsonschema

    def export_schema_dict(self, path):
        """
        Print the schema_dict in a json file.

        :param path: the path where to save the dict.format

        :return: nothing
        """
        self.save_json(self.schema_dict, path)
    
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
    
    """
    Functions used to translate jsonschema to schema_dict
    """
    def _create_data_schema(self, item):
        """
        Add a schema to self.schema_dict["DataSchema"]

        :param item: (key, value) of a dict. The key cotain the name of the schema and the value containt its content.

        return the schema dict.
        """
        name = item[0]
        content = item[1]
    
        schema = [dict(name=name,
                       type=self._get_schema_name(name),
                       many=("type" in content and content["type"] == "array"),
                       required=True)]
        self.schema_dict[DATASCHEMA] += schema
    
        return schema
    
    def _get_element_dict(self, item, required_list=None):
        """
        Parse an item (key, value) from the jsonschema and return the corresponding dict.
        
        :param item: An item from the jsonschema (key, value)
        :param required_list: A list of names corresponding to the required fields in the parent object
        
        :return A dict element for a schema_dict.
        """
        if required_list is None:
            required_list = []
            
        name = item[0]
        content = item[1]
        if "type" not in content:
            if "$ref" in content:
                return {
                    "name": name,
                    "type": self._get_ref(item),
                    "many": False,
                    "required": (name in required_list)
                }
            else:
                print("\nType missing for item: {}".format(name))
                raise TypeError("Type missing")
            
        if content["type"] == "object":
            return {
                "name": name,
                "type": self._get_object_schema(item),
                "many": False,
                "required": (name in required_list)
            }
        elif content["type"] == "array":
            return {
                "name": name,
                "type": self._get_array_schema(item),
                "many": True,
                "required": (name in required_list)
            }
        else:
            return self._get_field_dict(item, required_list)
    
    def _get_object_schema(self, item):
        """
        Transform an object item from the jsonschema in a dict for the schema_dict and update self.schema_dict.
        In jsonschema objects are similar to python dict.
        The object in jsonschema is in the following format:
        "object_name": {"type":"object", "properties":{"field1": {...}, "filed2": {...}}, "required": ["field1]}
        
        The schema_dict object use the format:
        {"schema_name": [{"name":"field1", "type": "field1_type", "many": False, "required":(True or False)}, ...]
        
        :param item: The jsonschema item (key, value)
        The format of the item is: ("object_name", {"type":"object", "properties":{"a": {...}, "b": {...}})
        
        :return: The schema name
        """
        name = item[0]
        content = item[1]
        schema_name = self._get_new_schema_name(name)
        ell = \
            {schema_name: [self._get_element_dict(i, self._get_required(content))
                           for i in content["properties"].items()]}
        self.schema_dict.update(ell)
        return schema_name
    
    def _get_array_schema(self, item):
        """
        Transform a array item from the jsonschema in a dict for the schema_dict and update self.schema_dict.
        In jsonschema arrays are similar to python lists.
        The object in jsonschema is in the following format:
        "object_name": {"type":"array", "items":{format_of_items}}

        The schema_dict object use the format:
        {"schema_name": [{"name":"field1", "type": "field1_type", "many": False, "required":(True or False)

        :param item: The jsonschema item (key, value)
        The format of the item is: ("object_name", {"type":"object", "properties":{"a": {...}, "b": {...}})

        :return: The schema name
        """
        name = item[0]
        content = item[1]["items"]
        schema_name = self._get_new_schema_name(name)
        if "type" in content and content["type"] == "object":
            self.schema_dict.update(
                {schema_name: [self._get_element_dict(i, self._get_required(content))
                               for i in content["properties"].items()]}
            )
        elif "$ref" in content:
            schema_name = self._get_ref((None, content))
        elif "type" in content and content["type"] != "array":
            return self._get_type(content["type"])
        else:
            self.schema_dict.update(
                {schema_name: [self._get_element_dict(i, self._get_required(content)) for i in content.items()]})
        return schema_name
       
    def _get_field_dict(self, item, required_list=None):
        """
        Transform a "normal" item from the jsonschema in a dict for the schema_dict and return it.
        This is used for items that will directly translate into fields.
        
        :param item: The jsonschema item in format (key, value)
        :param required_list: a list of the fields required in the parent object.
        
        :return: the schema_dict for this item
        """
        
        d = dict(
            name=item[0],
            type=self._get_type(item[1]["type"]),
            required=(item[0] in required_list),
            allow_none=("null" in item[1]["type"]),
            many=False)
        return d
    
    def _get_ref(self, item):
        """
        Get the name of the schema for a jsonschema reference.
        jsonschema definitions are parsed first and corresponign schema are created so a schema should exist
         corresponding to the reference.
        
        :param item: The jsonschema item in format (key, value)
        The value should be in the following format: {"$ref": "#/definitions/object_name"}
        
        :return The schema name (_get_schema_name(object_name))
        """
        content = item[1]
        ref = re.search("definitions/(.+)", content["$ref"]).group(1)
        return self._get_schema_name(ref)
    
    def _get_type(self, json_type):
        """
        Translate the type between jsonschema and schema_dict.
        
        :param json_type: the type in jsonschema
        
        :return: the type in schema_dict.
        """
        if type(json_type) is list:
            not_null_type = [i for i in json_type if i != "null"]
            if len(not_null_type) > 1:
                raise Warning("Warning: more than one type given")
            return self.types[not_null_type[0]]
        else:
            return self.types[json_type]

    @staticmethod
    def _get_schema_name(name, n=0):
        """
        Transform an element name into a schema name in order to create a schema corresponing to an object or array.
        The schema name use the following format:
        [name][n]Schema (for example if name is "values" and n is 3: Values3Schema)
        
        :param name: The name of the object or array.
        :param n: if n is different from 0, it is added to the schema name.
        
        :return: the corresponding schema name.
        """
        if n == 0:
            return name.capitalize() + "Schema"
        else:
            return name.capitalize() + str(n) + "Schema"
    
    def _get_new_schema_name(self, name, n=0):
        try_name = self._get_schema_name(name, n)
        
        if try_name in self.schema_dict:
            return self._get_new_schema_name(name, n+1)
        else:
            return try_name
    
    @staticmethod
    def _get_required(content):
        """
        Get the list of required name of it exist.
        
        :content: the dict which should have a "required" key.value
        
        :return: The required list or empty list.
        
        """
        return content.get("required", [])
    
    """
    Helper methods
    """
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

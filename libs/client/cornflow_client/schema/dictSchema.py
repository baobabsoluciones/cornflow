"""

"""
# Full imports
import re

# Imports from internal modules
from .dict_functions import gen_schema, ParameterSchema, sort_dict
from cornflow_client.constants import JSON_TYPES, DATASCHEMA


class DictSchema:
    """
    A json-schema to dict-schema parser
    """

    def __init__(self, jsonschema):
        """
        Class to manage internal dictionary schema

        :param jsonschema: a json schema
        """
        self.types = JSON_TYPES
        schema_dict = self.get_empty_schema()

        if "definitions" in jsonschema:
            for item in jsonschema["definitions"].items():
                self._get_element_dict(schema_dict=schema_dict, item=item)

        if "properties" in jsonschema:
            for item in jsonschema["properties"].items():
                self._get_element_dict(schema_dict=schema_dict, item=item)
                self._create_data_schema(
                    schema_dict=schema_dict,
                    item=item,
                    required_list=jsonschema.get("required"),
                )
        self.schema = schema_dict

    def get_schema(self):
        return self.schema

    @staticmethod
    def get_empty_schema():
        """
        Create un empty schema dict
        """
        return {DATASCHEMA: []}

    def _create_data_schema(self, schema_dict, item, required_list=None):
        """
        Add a schema to schema_dict[DATASCHEMA]

        :param item: (key, value) of a dict. The key contains the name of the schema
            and the value contains its content.

        return the schema dict.
        """
        name, content = item
        if required_list is None:
            required_list = []

        schema = dict(
            name=name,
            type=self._get_type_or_new_schema(item),
            many=("type" in content and content["type"] == "array"),
            required=name in required_list,
        )
        schema_dict[DATASCHEMA].append(schema)

        return schema

    def _get_element_dict(self, schema_dict, item, required_list=None):
        """
        Parse an item (key, value) from the jsonschema and return the corresponding dict.

        :param item: An item from the jsonschema (key, value)
        :param required_list: A list of names corresponding to the required fields in the parent object

        :return A dict element for a schema_dict.
        """
        if required_list is None:
            required_list = []

        name, content = item
        if "type" not in content:
            if "$ref" in content:
                return {
                    "name": name,
                    "type": self._get_ref(item),
                    "many": False,
                    "required": (name in required_list),
                }
            else:
                print(f"\nType missing for item: {name}")
                raise TypeError("Type missing")

        if content["type"] == "object":
            return {
                "name": name,
                "type": self._get_object_schema(schema_dict=schema_dict, item=item),
                "many": False,
                "required": (name in required_list),
            }
        elif content["type"] == "array":
            return {
                "name": name,
                "type": self._get_array_schema(schema_dict=schema_dict, item=item),
                "many": True,
                "required": (name in required_list),
            }
        else:
            return self._get_field_dict(item, required_list)

    def _get_object_schema(self, schema_dict, item):
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
        name, content = item
        schema_name = self._get_new_schema_name(schema_dict=schema_dict, name=name)
        ell = {
            schema_name: [
                self._get_element_dict(
                    schema_dict=schema_dict,
                    item=i,
                    required_list=self._get_required(content),
                )
                for i in content["properties"].items()
            ]
        }
        schema_dict.update(ell)
        return schema_name

    def _get_array_schema(self, schema_dict, item):
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
        name, content = item
        content = content["items"]
        schema_name = self._get_new_schema_name(schema_dict=schema_dict, name=name)
        if "type" in content and content["type"] == "object":
            schema_dict.update(
                {
                    schema_name: [
                        self._get_element_dict(
                            schema_dict=schema_dict,
                            item=i,
                            required_list=self._get_required(content),
                        )
                        for i in content["properties"].items()
                    ]
                }
            )
        elif "$ref" in content:
            schema_name = self._get_ref((None, content))
        elif "type" in content and content["type"] != "array":
            return self._get_type(content["type"])
        else:
            schema_dict.update(
                {
                    schema_name: [
                        self._get_element_dict(
                            schema_dict=schema_dict,
                            item=i,
                            required_list=self._get_required(content),
                        )
                        for i in content.items()
                    ]
                }
            )
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
            many=False,
            strict=True,
        )
        return d

    def _get_ref(self, item):
        """
        Get the name of the schema for a jsonschema reference.
        jsonschema definitions are parsed first and corresponding schema are created so a schema should exist
         corresponding to the reference.

        :param item: The jsonschema item in format (key, value)
        The value should be in the following format: {"$ref": "#/definitions/object_name"}

        :return The schema name (_get_schema_name(object_name))
        """
        content = item[1]
        ref = re.search("definitions/(.+)", content["$ref"]).group(1)
        return self._get_schema_name(ref)

    def _get_type_or_new_schema(self, item):
        """
        returns a new schema or a type depending on the json_type
        """
        name, content = item
        if "type" not in content or content["type"] == "object":
            return self._get_schema_name(name)
        elif content["type"] == "array":
            return self._get_type_or_new_schema((name, content["items"]))
        else:
            return self._get_type(content["type"])

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
        Transform an element name into a schema name in order to create a schema corresponding to an object or array.
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

    def _get_new_schema_name(self, schema_dict, name, n=0):
        try_name = self._get_schema_name(name, n)

        if try_name in schema_dict:
            return self._get_new_schema_name(
                schema_dict=schema_dict, name=name, n=n + 1
            )
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

    def to_marshmallow(self):
        dict_params = self.schema
        result_dict = {}
        ordered = sort_dict(dict_params)
        tuplist = sorted(dict_params.items(), key=lambda v: ordered[v[0]])
        for key, params in tuplist:
            schema = ParameterSchema()
            # this line validates the list of parameters:
            params1 = schema.load(params, many=True)
            result_dict[key] = gen_schema(key, params1, result_dict)

        return result_dict[DATASCHEMA]

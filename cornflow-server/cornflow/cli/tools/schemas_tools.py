# Schemas
from .tools import get_type

schemas_imports = "from marshmallow import fields, Schema\n\n"

JSON_TYPES_TO_FIELDS = {
    "integer": "fields.Int",
    "string": "fields.Str",
    "number": "fields.Number",
    "boolean": "fields.Boolean",
    "array": "fields.List",
    "date": "fields.Date",
    "datetime": "fields.DateTime",
    "time": "fields.Time",
}


class SchemaGenerator:
    def __init__(self, schema, table_name, app_name):
        self.schema = schema
        self.table_name = table_name
        self.app_name = app_name

    def generate_schema_file_description(self):
        res = (
            '"""\n'
            f"This file contains the schemas used for the table {self.table_name} "
            f"defined in the application {self.app_name}\n"
            '"""\n'
        )
        return res

    def generate_edit_schema(self):
        res = ""
        for key, val in self.schema["properties"].items():
            if key == "id":
                continue
            ty, _ = get_type(val)
            res += f"    {key} = {JSON_TYPES_TO_FIELDS[ty]}("
            res += "required=False"
            res += ")\n"
        return res

    def generate_post_schema(self):
        res = ""
        for key, val in self.schema["properties"].items():
            ty, _ = get_type(val)
            res += f"    {key} = {JSON_TYPES_TO_FIELDS[ty]}("
            if key in self.schema["required"]:
                res += "required=True"
            else:
                res += "required=False"
            res += ")\n"
        return res

    @staticmethod
    def generate_bulk_schema(one_schema):
        res = f"    data = fields.List(fields.Nested({one_schema}), required=True)\n"
        return res

    def generate_put_bulk_schema_one(self):
        if not self.schema["properties"].get("id"):
            return "    id = fields.Int(required=True)\n"
        else:
            id_type = self.schema["properties"].get("id")["type"]
            return f"    id = {JSON_TYPES_TO_FIELDS[id_type]}(required=True)\n"

    def generate_schema(self):
        if not self.schema["properties"].get("id"):
            return "    id = fields.Int(required=True)\n"
        else:
            return "    pass\n"

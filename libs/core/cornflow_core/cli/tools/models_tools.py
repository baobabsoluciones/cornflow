# Models
model_shared_imports = (
    "# Import from libraries\n"
    "from cornflow_core.shared import db\n"
    "from cornflow_core.models import TraceAttributesModel\n"
    "from sqlalchemy.dialects.postgresql import ARRAY\n\n"
)
SP8 = 8 * " "
SP12 = 12 * " "
JSON_TYPES_TO_SQLALCHEMY = {
    "integer": "db.Integer",
    "string": "db.String(256)",
    "number": "db.Float",
    "boolean": "db.Boolean",
    "array": "ARRAY",
}


class ModelGenerator:
    def __init__(self, class_name, schema, parents_class, table_name, app_name):
        self.class_name = class_name
        self.schema = schema
        self.parents_class = parents_class
        self.table_name = table_name
        self.app_name = app_name

    def generate_model_description(self):
        res = '    """\n'
        res += f"    Model class for table {self.table_name} of the application {self.app_name}\n"
        res += f'    It inherits from :class:`{" and :class:".join(self.parents_class)}`\n\n'
        app_description = self.schema.get("description")
        if app_description is not None and app_description != "":
            if isinstance(app_description, dict):
                app_description = app_description["en"]
            res += f"    Description of the app: {app_description}\n\n"
        table_description = self.schema["properties"][self.table_name].get(
            "description"
        )
        if table_description is not None and table_description != "":
            if isinstance(table_description, dict):
                table_description = table_description["en"]
            res += f"    Description of the table: {table_description}\n\n"
        res += f"    The :class:`{self.class_name}` has the following fields: \n\n"
        for key, val in self.schema["properties"][self.table_name]["items"][
            "properties"
        ].items():
            if key != "id":
                if isinstance(val.get("description"), dict):
                    res += (
                        f'    - **{key}**: {val["type"]}. {val["description"]["en"]}\n'
                    )
                else:
                    res += f'    - **{key}**: {val["type"]}. {val.get("description") or ""}\n'
            else:
                if isinstance(val.get("description"), dict):
                    res += f'    - **{key}**: {val["type"]}. The primary key. {val["description"]["en"]}\n'
                else:
                    res += f'    - **{key}**: {val["type"]}. The primary key. {val.get("description") or ""}\n'
        res += '    """\n'
        return res

    def generate_table_name(self):
        res = "    # Table name in the database\n"
        if self.app_name is None:
            res += f'    __tablename__ = "{self.table_name}"\n'
        else:
            res += f'    __tablename__ = "{self.app_name}_{self.table_name}"\n'
        return res

    def generate_model_fields(self):
        schema_table = self.schema["properties"][self.table_name]["items"]

        def has_id(schema):
            for prop in schema:
                if prop == "id":
                    return True
            return False

        res = "    # Model fields\n"
        if not has_id(schema_table["properties"]):
            res += f"    id = db.Column(db.Integer, primary_key=True, autoincrement=True)\n"
        for key, val in schema_table["properties"].items():
            nullable = False
            res += f"    {key} = db.Column("
            types = val["type"]
            if isinstance(types, list):
                nullable = True
                if types[0] == "null":
                    types = types[1]
                else:
                    types = types[0]
            res += JSON_TYPES_TO_SQLALCHEMY[types]
            if val.get("foreign_key"):
                foreign_table, foreign_prop = val["foreign_key"].split(".")
                if self.app_name is not None:
                    foreign_table = self.app_name + "_" + foreign_table

                res += f', db.ForeignKey("{foreign_table}.{foreign_prop}")'
            if key in schema_table["required"] and not nullable:
                res += ", nullable=False"
            else:
                res += ", nullable=True"
            if key == "id":
                res += ", primary_key=True"
            res += ")\n"
        return res

    def generate_model_init(self):
        keys = self.schema["properties"][self.table_name]["items"]["properties"].keys()
        res = "    def __init__(self, data):\n"
        res += SP8 + "super().__init__()\n"
        for key in keys:
            res += SP8 + f'self.{key} = data.get("{key}")\n'

        return res

    def generate_model_repr_str(self):
        res = "    def __repr__(self):\n"
        res += SP8 + '"""\n'
        res += SP8 + f"Method to represent the class :class:`{self.class_name}`\n\n"
        res += SP8 + f":return: The representation of the :class:`{self.class_name}`\n"
        res += SP8 + ":rtype: str\n"
        res += SP8 + '"""\n'
        res += SP8 + f"return '<{self.table_name.title()} ' + str(self.id) + '>'\n\n"

        res += "    def __str__(self):\n"
        res += SP8 + '"""\n'
        res += (
            SP8
            + f"Method to print a string representation of the class :class:`{self.class_name}`\n\n"
        )
        res += SP8 + f":return: The representation of the :class:`{self.class_name}`\n"
        res += SP8 + ":rtype: str\n"
        res += SP8 + '"""\n'
        res += SP8 + f"return self.__repr__()"
        return res

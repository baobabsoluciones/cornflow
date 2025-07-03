from .tools import get_type

# Models
model_shared_imports = (
    "# Import from libraries\n"
    "from cornflow.shared import db\n"
    "from cornflow.models.meta_models import TraceAttributesModel\n"
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
    "date": "db.Date",
    "datetime": "db.DateTime",
    "time": "db.Time",
}


class ModelGenerator:
    def __init__(self, class_name, schema, parents_class, table_name, app_name):
        self.class_name = class_name
        self.schema = schema
        self.parents_class = parents_class
        self.table_name = table_name
        self.app_name = app_name

    def _format_description(self, description_obj, prefix=""):
        """Formats a description object (str, dict, or None) into a string."""
        if description_obj is None or description_obj == "":
            return ""
        if isinstance(description_obj, dict):
            # Assuming 'en' key exists if it's a dict
            desc_text = description_obj.get("en", "")
        else:
            desc_text = str(description_obj)
        return f"{prefix}{desc_text}\n\n" if desc_text else ""

    def _format_field_description(self, key, val):
        """Formats the description line for a single model field."""
        desc_text = self._format_description(val.get("description")).strip()
        primary_key_text = " The primary key." if key == "id" else ""
        return f'    - **{key}**: {val["type"]}.{primary_key_text} {desc_text}\n'

    def generate_model_description(self):
        """Generates the model's docstring description."""
        lines = [
            '    """\n',
            f"    Model class for table {self.table_name} of the application {self.app_name}\n",
            f'    It inherits from :class:`{" and :class:".join(self.parents_class)}`\n\n',
        ]

        app_desc = self.schema.get("description")
        lines.append(self._format_description(app_desc, "Description of the app: "))

        table_desc = self.schema["properties"][self.table_name].get("description")
        lines.append(self._format_description(table_desc, "Description of the table: "))

        lines.append(
            f"    The :class:`{self.class_name}` has the following fields: \n\n"
        )

        fields = self.schema["properties"][self.table_name]["items"]["properties"]
        for key, val in fields.items():
            lines.append(self._format_field_description(key, val))

        lines.append('    """\n')
        return "".join(lines)

    def generate_table_name(self):
        res = "    # Table name in the database\n"
        if self.app_name is None:
            res += f'    __tablename__ = "{self.table_name}"\n'
        else:
            res += f'    __tablename__ = "{self.app_name}_{self.table_name}"\n'
        return res

    def _generate_field_definition(self, key, val, schema_table):
        """Generates the db.Column definition string for a single field."""
        parts = [f"    {key} = db.Column("]
        ty, nullable = get_type(val)
        parts.append(JSON_TYPES_TO_SQLALCHEMY[ty])

        # Handle foreign key
        if val.get("foreign_key"):
            foreign_table, foreign_prop = val["foreign_key"].split(".")
            if self.app_name is not None:
                foreign_table = self.app_name + "_" + foreign_table
            parts.append(f', db.ForeignKey("{foreign_table}.{foreign_prop}")')

        # Handle nullability
        is_required = key in schema_table.get("required", [])
        if is_required and not nullable:
            parts.append(", nullable=False")
        else:
            parts.append(", nullable=True")

        # Handle primary key for 'id' specifically
        if key == "id":
            parts.append(", primary_key=True")

        parts.append(")")
        return "".join(parts) + "\n"

    def generate_model_fields(self):
        """Generates the SQLAlchemy model field definitions."""
        schema_table = self.schema["properties"][self.table_name]["items"]
        properties = schema_table.get("properties", {})

        lines = ["    # Model fields\n"]

        # Add default ID if not present in schema
        if "id" not in properties:
            lines.append(
                "    id = db.Column(db.Integer, primary_key=True, autoincrement=True)\n"
            )

        # Generate definition for each field in the schema
        for key, val in properties.items():
            lines.append(self._generate_field_definition(key, val, schema_table))

        return "".join(lines)

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
        res += SP8 + "return self.__repr__()"
        return res

    def generate_imports(self):
        # Imports from libraries
        res = model_shared_imports
        return res

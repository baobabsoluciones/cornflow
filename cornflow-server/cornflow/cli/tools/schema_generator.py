# Import from libraries
import os
import re
import sys
import json
import importlib.util
from distutils.dir_util import copy_tree
from unittest.mock import MagicMock

import click
from flask_sqlalchemy import SQLAlchemy
import shutil
from pytups import TupList, SuperDict
from sqlalchemy.dialects.postgresql import TEXT, JSON
from sqlalchemy.sql.sqltypes import Integer


class SchemaGenerator:
    def __init__(self, path, output_path=None, ignore_files=None, leave_bases=False):
        self.path = path
        self.tmp_path = os.path.join(os.getcwd(), "tmp_files")
        self.output_path = output_path or "./output_schema.json"
        self.ignore_files = ignore_files or []
        self.leave_bases = leave_bases or False
        self.parents = dict()
        self.data = SuperDict()
        self.model_table = dict()
        self.table_model = dict()

    def main(self):
        os.mkdir(self.tmp_path)

        copy_tree(self.path, self.tmp_path)

        files = (
            TupList(os.listdir(self.tmp_path))
            .vfilter(
                lambda v: v.endswith(".py")
                and v != "__init__.py"
                and v != "__pycache__"
                and v not in self.ignore_files
            )
            .vapply(lambda v: (os.path.join(self.tmp_path, v), v[:-3]))
        )

        self.mock_packages(files)

        self.parse(files)

        self.inherit()

        schema = self.to_schema()

        with open(self.output_path, "w") as fd:
            json.dump(schema, fd, indent=2)
        self.clear()
        return 0

    def mock_packages(self, files):
        # Mocking all relative imports
        for file_path, file_name in files:
            with open(file_path, "r") as fd:
                text = fd.read()
            # SonarQube ReDoS FP: Pattern uses .+ but operates on Python source code
            # within a developer CLI tool, making ReDoS risk negligible.
            parents = re.findall(r"class (.+)\((.+)\):", text)
            for cl, parent in parents:
                self.parents[cl] = parent.replace(" ", "")
            libs = re.findall(r"from ((\.+\w+)+) import (\w+)", text)
            for lib in libs:
                text = text.replace(lib[0], "mockedpackage")
            with open(file_path, "w") as fd:
                fd.write(text)

        sys.modules["mockedpackage"] = MagicMock()

    def _load_module(self, file_path, file_name):
        """Loads a Python module dynamically from a file path."""
        try:
            spec = importlib.util.spec_from_file_location(file_name, file_path)
            if spec is None or spec.loader is None:
                click.echo(f"Warning: Could not create spec for {file_path}")
                return None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception as e:
            click.echo(f"Error loading module {file_name}: {e}")
            return None

    def _process_module(self, mod):
        """Processes a loaded module to find and parse model classes."""
        if mod is None:
            return

        models_in_mod = SuperDict(mod.__dict__).kfilter(lambda k: k in self.parents)
        for model_name, model_class in models_in_mod.items():
            processed_data = self._process_model(model_name, model_class, mod)
            if processed_data:
                table_name, props = processed_data
                self._process_properties(table_name, props)

    def _get_model_properties(self, model_name, model_class, mod):
        """Extracts properties (props) from a model class, handling mocks and abstract classes."""
        if isinstance(model_class, MagicMock):
            # Handle mocked models (often from relative imports)
            if not isinstance(mod.__dict__[model_name]._mock_return_value, dict):
                return None
            return mod.__dict__[model_name]._mock_return_value
        elif getattr(model_class, "__abstract__", False):
            # Handle abstract base models
            self.parents[model_name] = None  # Mark as a base parent
            return model_class.__dict__
        elif hasattr(model_class, "__table__"):
            # Handle concrete SQLAlchemy models
            self.parents[model_name] = None  # Mark as a base parent
            tmp = model_class.__dict__
            props = {"__tablename__": tmp.get("__tablename__")}
            # Extract columns directly from the __table__ object
            for col in model_class.__table__.columns:
                # Use col.key instead of internal __dict__['key']
                # Use col instead of iterating through proxy_set, as col represents the Column object
                props[col.key] = col
            return props
        else:
            # Not a recognized model type
            return None

    def _process_model(self, model_name, model_class, mod):
        """Processes a single model class to get its properties and initialize schema."""
        props = self._get_model_properties(model_name, model_class, mod)
        if props is None:
            return None

        table_name = props.get("__tablename__", model_name)

        # Initialize schema structure for this table
        self.data[table_name] = SuperDict(
            type="array", items=dict(properties=dict(), required=[])
        )

        # Mark for removal if it's a base class without a table and we want to remove bases
        if not props.get("__tablename__") and not self.leave_bases:
            self.data[table_name]["remove"] = True

        # Update model/table name mappings
        self.model_table[model_name] = table_name
        self.table_model[table_name] = model_name

        return table_name, props

    def _process_properties(self, table_name, props):
        """Iterates through model properties and processes columns."""
        forget_keys = ["created_at", "updated_at", "deleted_at"]
        db = SQLAlchemy()

        for key, val in props.items():
            if key in forget_keys or key.startswith("_"):
                continue
            # Check if it's a SQLAlchemy Column or a proxied Column from __table__
            if isinstance(val, (db.Column, Column)):
                self._process_column(table_name, key, val)
            # Potentially handle other property types here if needed

    def _process_column(self, table_name, key, column_obj):
        """Processes a single db.Column object to update the JSON schema."""
        db = SQLAlchemy()
        type_converter = {
            db.String: "string",
            TEXT: "string",
            JSON: "object",
            Integer: "integer",
            db.Integer: "integer",
            db.Boolean: "boolean",
            db.SmallInteger: "integer",
            db.Float: "number",
            # Represent dates as strings in JSON schema (format: date)
            db.Date: "string",
            # Represent datetimes as strings (format: date-time)
            db.DateTime: "string",
            # Represent time as string (format: time)
            db.Time: "string",
            # Consider how to represent LargeBinary - maybe string with format 'binary'?
        }
        type_col = "null"
        # Access the column type directly via column_obj.type
        column_type = column_obj.type
        for possible_type_class, repr_type in type_converter.items():
            # Use isinstance for robust type checking
            if isinstance(column_type, possible_type_class):
                type_col = repr_type
                break  # Found the type

        if type_col == "null":
            click.echo(
                f"Warning: Unknown column type '{column_type}' for {table_name}.{key}"
            )
            type_col = "string"

        self.data[table_name]["items"]["properties"][key] = SuperDict(type=type_col)

        # Add format for date/time types
        if isinstance(column_type, db.Date):
            self.data[table_name]["items"]["properties"][key]["format"] = "date"
        elif isinstance(column_type, db.DateTime):
            self.data[table_name]["items"]["properties"][key]["format"] = "date-time"
        elif isinstance(column_type, db.Time):
            self.data[table_name]["items"]["properties"][key]["format"] = "time"

        # Handle foreign keys using column_obj.foreign_keys
        if column_obj.foreign_keys:
            # Assuming only one foreign key per column for simplicity here
            fk = next(iter(column_obj.foreign_keys))
            self.data[table_name]["items"]["properties"][key][
                "foreign_key"
            ] = fk.target_fullname

        # Handle nullability using column_obj.nullable
        if not column_obj.nullable:
            # Ensure 'required' list exists before appending
            if "required" not in self.data[table_name]["items"]:
                self.data[table_name]["items"]["required"] = []
            if key not in self.data[table_name]["items"]["required"]:
                self.data[table_name]["items"]["required"].append(key)

    def parse(self, files):
        SQLAlchemy()
        try:
            for file_path, file_name in files:
                mod = self._load_module(file_path, file_name)
                if mod:
                    self._process_module(mod)

            # Potential db.session cleanup if it was actually used and persisted
            # If db is only used for type comparison, this might not be needed
            # db.session.close() # Consider if this is necessary

        except Exception as err:
            click.echo(f"An error occurred during parsing: {err}")

    def inherit(self):
        all_classes = set(self.parents.keys())
        not_treated = set(all_classes)
        treated = {"db.Model"}
        while not_treated:
            for model in not_treated:
                parent = self.parents[model]
                if parent is None:
                    treated.add(model)
                    continue
                if parent not in treated:
                    continue
                treated.add(model)
                if parent == "db.Model":
                    continue
                table_name = self.model_table[model]
                parent_props = self.data[self.model_table[parent]]["items"][
                    "properties"
                ]
                parent_requirements = self.data[self.model_table[parent]]["items"][
                    "required"
                ]
                self.data[table_name]["items"]["properties"] = SuperDict(
                    **parent_props, **self.data[table_name]["items"]["properties"]
                )
                self.data[table_name]["items"]["required"] += parent_requirements
            not_treated -= treated
        if not self.leave_bases:
            self.data = self.data.vfilter(lambda v: not v.get("remove", False))

    def clear(self):
        if os.path.isdir(self.tmp_path):
            shutil.rmtree(self.tmp_path)

    def to_schema(self):
        return {
            "$schema": "https://json-schema.org/schema#",
            "type": "object",
            "properties": self.data,
            "required": list(self.data.keys()),
        }

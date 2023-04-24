# Import from libraries
import os
import re
import sys
import json
import importlib.util
from distutils.dir_util import copy_tree
from unittest.mock import MagicMock
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
            parents = re.findall(r"class (.+)\((.+)\):", text)
            for cl, parent in parents:
                self.parents[cl] = parent.replace(" ", "")
            libs = re.findall(r"from ((\.+\w+)+) import (\w+)", text)
            for lib in libs:
                text = text.replace(lib[0], "mockedpackage")
            with open(file_path, "w") as fd:
                fd.write(text)

        sys.modules["mockedpackage"] = MagicMock()

    def parse(self, files):
        forget_keys = ["created_at", "updated_at", "deleted_at"]
        db = SQLAlchemy()
        try:
            for file_path, file_name in files:

                spec = importlib.util.spec_from_file_location(file_name, file_path)
                mod = importlib.util.module_from_spec(spec)

                spec.loader.exec_module(mod)

                models = SuperDict(mod.__dict__).kfilter(lambda k: k in self.parents)
                for model in models:
                    if isinstance(models[model], MagicMock):
                        # Models that inherit from other models that are relatively imported
                        if not isinstance(mod.__dict__[model]._mock_return_value, dict):
                            continue
                        props = mod.__dict__[model]._mock_return_value
                    elif mod.__dict__[model].__dict__.get("__abstract__"):
                        # BaseDataModel
                        props = mod.__dict__[model].__dict__
                        self.parents[model] = None
                    else:
                        # Models that inherit from other models that are imported from libraries
                        self.parents[model] = None
                        tmp = mod.__dict__[model].__dict__
                        props = {"__tablename__": tmp.get("__tablename__")}
                        for col in tmp["__table__"]._columns:
                            props[col.__dict__["key"]] = next(iter(col.proxy_set))
                    table_name = props.get("__tablename__", model)
                    self.data[table_name] = SuperDict(
                        type="array", items=dict(properties=dict(), required=[])
                    )
                    if not props.get("__tablename__") and not self.leave_bases:
                        self.data[table_name]["remove"] = True
                    self.model_table[model] = table_name
                    self.table_model[table_name] = model
                    for key, val in props.items():
                        if key in forget_keys:
                            continue
                        elif isinstance(val, db.Column):
                            type_converter = {
                                db.String: "string",
                                TEXT: "string",
                                JSON: "object",
                                Integer: "integer",
                                db.Integer: "integer",
                                db.Boolean: "boolean",
                                db.SmallInteger: "integer",
                                db.Float: "number",
                            }
                            type_col = "null"
                            for possible_type, repr_type in type_converter.items():
                                if isinstance(val.type, possible_type):
                                    type_col = repr_type
                            if type_col == "null":
                                raise Exception("Unknown column type")

                            self.data[table_name]["items"]["properties"][
                                key
                            ] = SuperDict(type=type_col)
                            if val.foreign_keys:
                                fk = list(val.foreign_keys)[0]
                                self.data[table_name]["items"]["properties"][key][
                                    "foreign_key"
                                ] = fk._colspec
                            if not val.nullable:
                                self.data[table_name]["items"]["required"].append(key)

            db.session.close()
        except Exception as err:
            print(err)

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
            "$schema": "http://json-schema.org/schema#",
            "type": "object",
            "properties": self.data,
            "required": list(self.data.keys()),
        }

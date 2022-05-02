import importlib.util
import unittest
from unittest.mock import MagicMock
import os
import sys
import json
import shutil

from click.testing import CliRunner
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import TEXT, JSON
from sqlalchemy.sql.sqltypes import Integer
from pytups import TupList, SuperDict
from cornflow_core.models import TraceAttributesModel
from cornflow_core.cli.generate_from_schema import generate_from_schema

sys.modules["mockedpackage"] = MagicMock()
path_to_tests = os.path.dirname(os.path.abspath(__file__))


class GenerationTests(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.full_inst_path = self._get_path("./data/instance.json")
        self.full_inst = SuperDict.from_dict(self.import_schema(self.full_inst_path))
        # Removing parameter tables
        self.full_inst["properties"] = self.full_inst["properties"].vfilter(
            lambda v: v["type"] == "array"
        )
        self.one_tab_inst_path = self._get_path("./data/one_table.json")
        self.one_tab_inst = SuperDict.from_dict(
            self.import_schema(self.one_tab_inst_path)
        )
        self.app_name = "test"
        self.second_app_name = "test_sec"
        self.default_output_path = self._get_path("./data/output")
        self.other_output_path = self._get_path("./data/output_path")
        self.last_path = self.default_output_path
        self.all_methods = TupList(
            ["getOne", "getAll", "deleteOne", "deleteAll", "update", "post"]
        )

    def tearDown(self):
        if os.path.isdir(self.last_path):
            shutil.rmtree(self.last_path)

    @staticmethod
    def _get_path(rel_path):
        return os.path.join(path_to_tests, rel_path)

    @staticmethod
    def import_schema(path):
        with open(path, "r") as fd:
            schema = json.load(fd)
        return schema

    def test_base(self):
        runner = CliRunner()
        result = runner.invoke(
            generate_from_schema,
            [
                "-p",
                self.full_inst_path,
                "-a",
                self.app_name,
                "-o",
                self.other_output_path,
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.last_path = self.other_output_path
        self.check(output_path=self.other_output_path)

    def test_one_table_schema(self):
        runner = CliRunner()
        result = runner.invoke(
            generate_from_schema,
            [
                "-p",
                self.one_tab_inst_path,
                "-a",
                self.app_name,
                "-o",
                self.other_output_path,
            ],
        )

        self.assertEqual(result.exit_code, 0)

        instance = SuperDict.from_dict({"properties": {"data": self.one_tab_inst}})
        self.last_path = self.other_output_path
        self.check(instance=instance, output_path=self.other_output_path)

    def test_one_table_one_option(self):
        runner = CliRunner()
        result = runner.invoke(
            generate_from_schema,
            [
                "-p",
                self.one_tab_inst_path,
                "-a",
                self.app_name,
                "--one",
                "newname",
                "-o",
                self.other_output_path,
            ],
        )

        self.assertEqual(result.exit_code, 0)

        instance = SuperDict.from_dict({"properties": {"newname": self.one_tab_inst}})
        self.last_path = self.other_output_path
        self.check(instance=instance, output_path=self.other_output_path)

    def test_remove_method(self):
        runner = CliRunner()
        result = runner.invoke(
            generate_from_schema,
            [
                "-p",
                self.full_inst_path,
                "-a",
                self.second_app_name,
                "-o",
                self.other_output_path,
                "-r",
                "delete_detail",
                "-r",
                "put_detail",
                "-r",
                "get_detail",
                "-r",
                "patch_detail",
            ],
        )

        self.assertEqual(result.exit_code, 0)

        include_methods = self.all_methods.vfilter(
            lambda v: v not in ["deleteOne", "update", "getOne"]
        )
        self.last_path = self.other_output_path
        self.check(
            output_path=self.other_output_path,
            include_methods=include_methods,
            app_name=self.second_app_name,
        )

    def check(
        self, instance=None, output_path=None, include_methods=None, app_name=None
    ):
        if app_name is None:
            app_name = self.app_name
        db = SQLAlchemy()
        instance = instance or self.full_inst
        output_path = output_path or self.default_output_path
        include_methods = include_methods or self.all_methods
        models_dir = os.path.join(output_path, "models")
        endpoints_dir = os.path.join(output_path, "endpoints")
        schemas_dir = os.path.join(output_path, "schemas")
        created_dirs = [output_path, models_dir, endpoints_dir, schemas_dir]

        # Checks that the directories have been created
        for path in created_dirs:
            self.assertTrue(os.path.isdir(self._get_path(path)))

        # Checks that each file has been created
        created_dirs = created_dirs[1:4]
        files = (
            instance["properties"]
            .keys_tl()
            .vapply(lambda v: (app_name + "_" + v + ".py", v))
        )
        absolute_paths = [
            os.path.join(path, file) for path in created_dirs for file, _ in files
        ]
        for path_file in absolute_paths:
            self.assertTrue(os.path.exists(self._get_path(path_file)))
            if os.path.exists(path_file):
                with open(path_file, "r") as fd:
                    txt = fd.read()
                packages_to_mock = [
                    "..shared.utils",
                    ".meta_model",
                    ".meta_resource",
                    "..shared.const",
                    "..shared.authentification",
                    "..models",
                    "..schemas",
                ]
                for package in packages_to_mock:
                    txt = txt.replace(package, "mockedpackage")

                with open(path_file, "w") as fd:
                    fd.write(txt)

        # Checks that the models have the correct methods and attributes
        for file, table in files:
            class_name = self.snake_to_camel(app_name + "_" + table + "_model")
            file_path = os.path.join(models_dir, file)
            spec = importlib.util.spec_from_file_location(class_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Checks correct inheritance

            self.assertTrue(issubclass(mod.__dict__[class_name], TraceAttributesModel))

            # Checks that the all the columns are declared, have the correct type
            props_and_methods = mod.__dict__[class_name].__dict__
            props = dict()
            for col in props_and_methods["__table__"]._columns:
                props[col.key] = next(iter(col.proxy_set))

            expected_prop = instance["properties"][table]["items"]["properties"]
            for prop in expected_prop:
                self.assertIn(prop, props)
                types = expected_prop[prop]["type"]
                if isinstance(types, list):
                    types = TupList(types).vfilter(lambda v: v != "null")[0]

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
                actual_type = "null"
                for possible_type, repr_type in type_converter.items():
                    if isinstance(props[prop].type, possible_type):
                        actual_type = repr_type

                self.assertEqual(types, actual_type)
            # Checks that all the methods are declared
            expected_methods = ["__init__", "__repr__", "__str__"]
            expected_methods = set(expected_methods)
            for method in expected_methods:
                self.assertIn(method, props_and_methods.keys())

        # Checks that the schemas have the correct methods and attributes
        for file, table in files:
            mod_name = self.snake_to_camel(app_name + "_" + table + "_schema")
            class_names = [
                self.snake_to_camel(app_name + "_" + table + "_" + type_schema)
                for type_schema in ["response", "edit_request", "post_request"]
            ]
            file_path = os.path.join(schemas_dir, file)
            spec = importlib.util.spec_from_file_location(mod_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            existing_classes = list(mod.__dict__.keys())
            # Checks that all the schemas are created
            for class_name in class_names:
                self.assertIn(class_name, existing_classes)
                props = mod.__dict__[class_name]._declared_fields
                # Checks that the classes have all the attributes
                expected_prop = instance["properties"][table]["items"]["properties"]
                expected_prop = TupList(expected_prop).vfilter(lambda v: v != "id")
                for prop in expected_prop:
                    self.assertIn(prop, props)

        # Checks that the endpoints have all the methods
        for file, table in files:
            mod_name = self.snake_to_camel(app_name + "_" + table + "_endpoint")
            class_names = [self.snake_to_camel(app_name + "_" + table + "_endpoint")]
            if (
                "getOne" in include_methods
                or "deleteOne" in include_methods
                or "update" in include_methods
            ):
                class_names.append(
                    self.snake_to_camel(app_name + "_" + table + "_details_endpoint")
                )
            file_path = os.path.join(endpoints_dir, file)
            spec = importlib.util.spec_from_file_location(mod_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            existing_classes = list(mod.__dict__.keys())
            # Checks that all the endpoints are created
            for class_name in class_names:
                self.assertIn(class_name, existing_classes)

            api_methods = {
                "get_detail": "GET",
                "get_list": "GET",
                "post_list": "POST",
                "delete_detail": "DELETE",
                "put_detail": "PUT",
                "patch_detail": "PATCH",
            }
            # Checks the methods of the first endpoint
            include_methods_e1 = [
                method_name
                for method_name in include_methods
                if method_name in ["get_list", "post_list"]
            ]
            props_and_methods = mod.__dict__[class_names[0]].methods
            for method_name in include_methods_e1:
                self.assertIn(api_methods[method_name], props_and_methods)

            # Checks the methods of the details endpoint
            if len(class_names) == 2:
                include_methods_e2 = [
                    method_name
                    for method_name in include_methods
                    if method_name
                    in ["get_detail", "put_detail", "delete_detail", "patch_detail"]
                ]
                props_and_methods = mod.__dict__[class_names[1]].methods
                for method_name in include_methods_e2:
                    self.assertIn(api_methods[method_name], props_and_methods)

    @staticmethod
    def snake_to_camel(name):
        return "".join(word.title() for word in name.split("_"))

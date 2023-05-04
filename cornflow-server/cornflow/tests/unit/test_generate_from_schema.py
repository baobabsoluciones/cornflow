# Imports from libraries
import importlib.util
import json
import os
import shutil
import sys
import unittest

from click.testing import CliRunner
from flask_sqlalchemy import SQLAlchemy
from pytups import TupList, SuperDict
from sqlalchemy.dialects.postgresql import TEXT, JSON
from sqlalchemy.sql.sqltypes import Integer
from unittest.mock import MagicMock

# Imports from internal modules
from cornflow.models.meta_models import TraceAttributesModel
from cornflow.cli import cli
from cornflow.cli.schemas import APIGenerator

sys.modules["mockedpackage"] = MagicMock()
path_to_tests = os.path.dirname(os.path.abspath(__file__))


class GenerationTests(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.full_inst_path = self._get_path(
            "../data/instance_gfs.json")
        self.inst_path2 = self._get_path("../data/instance2_gfs.json")
        self.full_inst = SuperDict.from_dict(self.import_schema(self.full_inst_path))
        # Removing parameter tables
        self.full_inst["properties"] = self.full_inst["properties"].vfilter(
            lambda v: v["type"] == "array"
        )
        self.one_tab_inst_path = self._get_path("../data/one_table_gfs.json")
        self.one_tab_inst = SuperDict.from_dict(
            self.import_schema(self.one_tab_inst_path)
        )
        self.app_name = "test"
        self.second_app_name = "test_sec"
        self.default_output_path = self._get_path("../data/output")
        self.other_output_path = self._get_path("../data/output_path")
        self.last_path = self.default_output_path
        self.all_methods = TupList(
            [
                "get_detail",
                "get_list",
                "delete_detail",
                "put_detail",
                "patch_detail",
                "post_list",
                "put_bulk",
                "post_bulk",
            ]
        )
        self.endpoints_methods_path = self._get_path("../data/endpoints_methods.json")
        self.endpoints_access_path = self._get_path("../data/endpoints_access.json")

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
            cli,
            [
                "schemas",
                "generate_from_schema",
                "-p",
                self.full_inst_path,
                "-a",
                self.app_name,
                "-o",
                self.other_output_path,
            ]
        )

        self.assertEqual(result.exit_code, 0)
        self.last_path = self.other_output_path
        self.check(output_path=self.other_output_path)

    def test_one_table_schema(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schemas",
                "generate_from_schema",
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
            cli,
            [
                "schemas",
                "generate_from_schema",
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
            cli,
            [
                "schemas",
                "generate_from_schema",
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
            lambda v: v not in ["delete_detail", "put_detail", "get_detail", "patch_detail"]
        )
        self.last_path = self.other_output_path
        self.check(
            output_path=self.other_output_path,
            include_methods=include_methods,
            app_name=self.second_app_name,
        )

    def test_endpoints_methods(self):

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schemas",
                "generate_from_schema",
                "-p",
                self.full_inst_path,
                "-a",
                "test3",
                "-o",
                self.other_output_path,
                "-m",
                self.endpoints_methods_path,
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.last_path = self.other_output_path
        self.check(output_path=self.other_output_path, app_name="test3")

    def test_endpoints_access(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schemas",
                "generate_from_schema",
                "-p",
                self.full_inst_path,
                "-a",
                "test4",
                "-o",
                self.other_output_path,
                "-e",
                self.endpoints_access_path,
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.last_path = self.other_output_path
        self.check(output_path=self.other_output_path, app_name="test4")

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
                    " cornflow.models ",
                    " cornflow.schemas ",
                    " cornflow.shared.authentication ",
                    " ..models ",
                    " ..schemas "
                ]
                for package in packages_to_mock:
                    txt = txt.replace(package, " mockedpackage ")

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
            class_names = []
            base = self.snake_to_camel(app_name + "_" + table + "_endpoint")
            details = self.snake_to_camel(app_name + "_" + table + "_details_endpoint")
            bulk = self.snake_to_camel(app_name + "_" + table + "_bulk_endpoint")
            if any(m in include_methods for m in ["get_list", "post_list"]):
                class_names += [base]
            if any(m in include_methods for m in ["get_detail", "delete_detail", "put_detail", "patch_detail"]):
                class_names += [details]
            if any(m in include_methods for m in ["put_bulk", "post_bulk"]):
                class_names += [bulk]
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
                "post_bulk": "POST",
                "put_bulk": "PUT",
            }
            # Checks the methods of the base endpoint
            if base in class_names:
                include_methods_base = [
                    method_name
                    for method_name in include_methods
                    if method_name in ["get_list", "post_list"]
                ]
                props_and_methods = mod.__dict__[base].methods
                for method_name in include_methods_base:
                    self.assertIn(api_methods[method_name], props_and_methods)

            # Checks the methods of the details endpoint
            if details in class_names:
                include_methods_details = [
                    method_name
                    for method_name in include_methods
                    if method_name
                    in ["get_detail", "put_detail", "delete_detail", "patch_detail"]
                ]
                props_and_methods = mod.__dict__[details].methods
                for method_name in include_methods_details:
                    self.assertIn(api_methods[method_name], props_and_methods)

            if bulk in class_names:
                include_methods_bulk = [
                    method_name
                    for method_name in include_methods
                    if method_name in ["post_bulk", "put_bulk"]
                ]
                props_and_methods = mod.__dict__[bulk].methods
                for method_name in include_methods_bulk:
                    self.assertIn(api_methods[method_name], props_and_methods)

    def test_get_id_type(self):
        api_gen = APIGenerator(schema_path=self.inst_path2, app_name=None)
        self.assertEqual(api_gen.get_id_type("employees"), "<string:idx>")
        self.assertEqual(api_gen.get_id_type("shifts"), "<int:idx>")
        self.assertEqual(api_gen.get_id_type("demand"), "<int:idx>")


    @staticmethod
    def snake_to_camel(name):
        return "".join(word.title() for word in name.split("_"))

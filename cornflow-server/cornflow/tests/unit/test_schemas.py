"""

"""

# General imports
import unittest

# Partial imports
from marshmallow import ValidationError, Schema, fields
from unittest.mock import patch

# Imports from environment
from cornflow_client import get_pulp_jsonschema, get_empty_schema
from cornflow_client.schema.dict_functions import gen_schema, ParameterSchema, sort_dict

# Imports from internal modules
from cornflow.app import create_app
from cornflow.tests.const import SCHEMA_URL
from cornflow.tests.custom_test_case import CustomTestCase


class SchemaGenerator(unittest.TestCase):
    data1 = [
        {
            "name": "filename",
            "required": True,
            "type": "String",
            "valid_values": ["hello.txt", "foo.py", "bar.png"],
            "metadata": {"description": "Should be a filename"},
        },
        {
            "name": "SomeBool",
            "metadata": {"description": "Just a bool"},
            "required": True,
            "type": "Boolean",
        },
        {
            "name": "NotRequiredBool",
            "metadata": {"description": "Another bool that's not required"},
            "required": False,
            "type": "Boolean",
        },
    ]

    def test_something(self):
        req1 = {"filename": "foo.py", "SomeBool": False}
        dynamic_schema = gen_schema("D1", self.data1)()
        dynamic_res1 = dynamic_schema.load(req1)

    def test_something_else(self):
        req2 = {"filename": "hi.txt", "SomeBool": True, "NotRequiredBool": False}
        dynamic_schema = gen_schema("D1", self.data1)()
        func_error = lambda: dynamic_schema.load(req2)
        self.assertRaises(ValidationError, func_error)

    def test_class(self):
        class CoefficientsSchema(Schema):
            name = fields.Str(required=True)
            value = fields.Float(required=True)

        params = [
            dict(name="name", type="String", required=True),
            dict(name="value", type="Float", required=True),
        ]
        schema = ParameterSchema()
        params1 = schema.load(params, many=True)
        CoefficientsSchema2 = gen_schema("CoefficientsSchema", params1)
        a = CoefficientsSchema2()
        b = CoefficientsSchema()
        good = dict(name="a", value=1)
        bad = dict(name=1, value="")
        a.load(good)
        b.load(good)
        func_error1 = lambda: a.load(bad)
        func_error2 = lambda: b.load(bad)
        self.assertRaises(ValidationError, func_error1)
        self.assertRaises(ValidationError, func_error2)

    def test_two_classes(self):

        dict_params = dict(
            CoefficientsSchema=[
                dict(name="name", type="String", required=True),
                dict(name="value", type="Float", required=True),
            ],
            ObjectiveSchema=[
                dict(name="name", type="String", required=False, allow_none=True),
                dict(
                    name="coefficients",
                    type="CoefficientsSchema",
                    many=True,
                    required=True,
                ),
            ],
        )
        result_dict = {}
        for key, params in dict_params.items():
            schema = ParameterSchema()
            params1 = schema.load(params, many=True)
            result_dict[key] = gen_schema(key, params1, result_dict)

        good = dict(
            name="objective",
            coefficients=[dict(name="a", value=1), dict(name="b", value=5)],
        )
        bad = dict(name=1)
        bad2 = dict(coefficients=[dict(name=1, value="")])
        oschema = result_dict["ObjectiveSchema"]()
        oschema.load(good)
        func_error1 = lambda: oschema.load(bad)
        func_error2 = lambda: oschema.load(bad2)
        self.assertRaises(ValidationError, func_error1)
        self.assertRaises(ValidationError, func_error2)

    def test_two_unordered_classes(self):

        dict_params = dict(
            ObjectiveSchema=[
                dict(name="name", type="String", required=False, allow_none=True),
                dict(
                    name="coefficients",
                    type="CoefficientsSchema",
                    many=True,
                    required=True,
                ),
            ],
            CoefficientsSchema=[
                dict(name="name", type="String", required=True),
                dict(name="value", type="Float", required=True),
            ],
        )
        result_dict = {}
        ordered = sort_dict(dict_params)
        tuplist = sorted(dict_params.items(), key=lambda v: ordered[v[0]])
        for key, params in tuplist:
            schema = ParameterSchema()
            params1 = schema.load(params, many=True)
            result_dict[key] = gen_schema(key, params1, result_dict)

        good = dict(
            name="objective",
            coefficients=[dict(name="a", value=1), dict(name="b", value=5)],
        )
        bad = dict(name=1)
        bad2 = dict(coefficients=[dict(name=1, value="")])
        oschema = result_dict["ObjectiveSchema"]()
        oschema.load(good)
        func_error1 = lambda: oschema.load(bad)
        func_error2 = lambda: oschema.load(bad2)
        self.assertRaises(ValidationError, func_error1)
        self.assertRaises(ValidationError, func_error2)


class TestSchemaEndpoint(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.schema = get_pulp_jsonschema()
        self.config = get_empty_schema(solvers=["cbc", "PULP_CBC_CMD"])
        self.url = SCHEMA_URL
        self.schema_name = "solve_model_dag"

    def test_get_schema(self):
        keys_to_check = [
            "solution_checks",
            "instance_checks",
            "config",
            "solution",
            "name",
            "instance",
        ]
        schemas = self.get_one_row(
            self.url + "{}/".format(self.schema_name),
            {},
            expected_status=200,
            check_payload=False,
            keys_to_check=keys_to_check,
        )
        self.assertIn("instance", schemas)
        self.assertIn("solution", schemas)
        self.assertEqual(schemas["instance"], self.schema)
        self.assertEqual(schemas["solution"], self.schema)
        self.assertEqual(schemas["config"], self.config)


class TestNewSchemaEndpointOpen(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = SCHEMA_URL

    def test_get_all_schemas(self):
        schemas = self.get_one_row(self.url, {}, 200, False, keys_to_check=["name"])
        dags = [{"name": dag} for dag in ["solve_model_dag", "gc", "timer"]]

        self.assertEqual(dags, schemas)


class TestNewSchemaEndpointNotOpen(CustomTestCase):
    def create_app(self):
        app = create_app("testing")
        app.config["OPEN_DEPLOYMENT"] = 0
        return app

    def setUp(self):
        super().setUp()
        self.url = SCHEMA_URL
        self.schema_name = "solve_model_dag"

    def test_get_all_schemas(self):
        schemas = self.get_one_row(self.url, {}, 200, False)
        self.assertEqual([], schemas)

    def test_get_one_schema(self):
        schema = self.get_one_row(
            self.url + "{}/".format(self.schema_name),
            {},
            expected_status=403,
            check_payload=False,
            keys_to_check=["error"],
        )
        self.assertEqual(
            {"error": "User does not have permission to access this dag"}, schema
        )


if __name__ == "__main__":
    unittest.main()

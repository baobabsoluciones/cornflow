import unittest
import json

from cornflow.schemas.schema_dict_functions import gen_schema, ParameterSchema, sort_dict
from cornflow.schemas.solution_log import LogSchema
from airflow_config.dags.model_functions import solve_model
from marshmallow import ValidationError, Schema, fields


class SchemaGenerator(unittest.TestCase):
    data1 = [
            {"name": "filename",
             "description": "Should be a filename",
             "required": True,
             "type": "String",
             "valid_values": ["hello.txt", "foo.py", "bar.png"]
             },
            {"name": "SomeBool",
             "description": "Just a bool",
             "required": True,
             "type": "Boolean",
             },
            {"name": "NotRequiredBool",
             "description": "Another bool that's not required",
             "required": False,
             "type": "Boolean"
             }
        ]

    def test_something(self):
        req1 = {"filename": "foo.py", "SomeBool": False}
        dynamic_schema = gen_schema("D1", self.data1)()
        dynamic_res1 = dynamic_schema.load(req1)

    def test_something_else(self):
        req2 = {"filename": "hi.txt", "SomeBool": True, "NotRequiredBool": False}
        dynamic_schema = gen_schema("D1", self.data1)()
        func_error = lambda :  dynamic_schema.load(req2)
        self.assertRaises(ValidationError, func_error)

    def test_class(self):
        class CoefficientsSchema(Schema):
            name = fields.Str(required=True)
            value = fields.Float(required=True)

        params = [dict(name='name', type='String', required=True),
                  dict(name='value', type='Float', required=True)]
        schema = ParameterSchema()
        params1 = schema.load(params, many=True)
        CoefficientsSchema2 = gen_schema('CoefficientsSchema', params1)
        a = CoefficientsSchema2()
        b = CoefficientsSchema()
        good = dict(name='a', value=1)
        bad = dict(name=1, value='')
        a.load(good)
        b.load(good)
        func_error1 = lambda: a.load(bad)
        func_error2 = lambda: b.load(bad)
        self.assertRaises(ValidationError, func_error1)
        self.assertRaises(ValidationError, func_error2)

    def test_two_classes(self):
        # class CoefficientsSchema(Schema):
        #     name = fields.Str(required=True)
        #     value = fields.Float(required=True)
        #
        # class ObjectiveSchema(Schema):
        #     name = fields.Str(required=False, allow_none=True)
        #     coefficients = fields.Nested(CoefficientsSchema, many=True, required=True)

        dict_params = \
            dict(CoefficientsSchema=
             [dict(name='name', type='String', required=True),
              dict(name='value', type='Float', required=True)],
             ObjectiveSchema=
             [dict(name='name', type='String', required=False, allow_none=True),
              dict(name='coefficients', type='CoefficientsSchema', many=True, required=True)]
             )
        result_dict = {}
        for key, params in dict_params.items():
            schema = ParameterSchema()
            params1 = schema.load(params, many=True)
            result_dict[key] = gen_schema(key, params1, result_dict)

        good = dict(name='objective', coefficients=[dict(name='a', value=1), dict(name='b', value=5)])
        bad = dict(name=1)
        bad2 = dict(coefficients=[dict(name=1, value='')])
        oschema = result_dict['ObjectiveSchema']()
        oschema.load(good)
        func_error1 = lambda: oschema.load(bad)
        func_error2 = lambda: oschema.load(bad2)
        self.assertRaises(ValidationError, func_error1)
        self.assertRaises(ValidationError, func_error2)

    def test_two_unordered_classes(self):

        dict_params = \
            dict(ObjectiveSchema=
             [dict(name='name', type='String', required=False, allow_none=True),
              dict(name='coefficients', type='CoefficientsSchema', many=True, required=True)],
                CoefficientsSchema=
             [dict(name='name', type='String', required=True),
              dict(name='value', type='Float', required=True)]
             )
        result_dict = {}
        ordered = sort_dict(dict_params)
        tuplist = sorted(dict_params.items(), key=lambda v: ordered[v[0]])
        for key, params in tuplist:
            schema = ParameterSchema()
            params1 = schema.load(params, many=True)
            result_dict[key] = gen_schema(key, params1, result_dict)

        good = dict(name='objective', coefficients=[dict(name='a', value=1), dict(name='b', value=5)])
        bad = dict(name=1)
        bad2 = dict(coefficients=[dict(name=1, value='')])
        oschema = result_dict['ObjectiveSchema']()
        oschema.load(good)
        func_error1 = lambda: oschema.load(bad)
        func_error2 = lambda: oschema.load(bad2)
        self.assertRaises(ValidationError, func_error1)
        self.assertRaises(ValidationError, func_error2)


class PuLPLogSchema(unittest.TestCase):
    with open('./cornflow/tests/data/gc_20_7.json', 'r') as f:
        data = json.load(f)

    config = dict(solver="PULP_CBC_CMD", timeLimit=10)

    def test_progress(self):
        solution, log, log_dict = solve_model(self.data, self.config)
        LS = LogSchema()
        LS.dump(log_dict)


if __name__ == '__main__':
    unittest.main()

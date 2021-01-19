from cornflow.schemas.schema_manager import SchemaManager
from unittest import TestCase
from cornflow.tests.data.dict_schema_example import dict_example


class TestSchemaManager(TestCase):
    
    def setUp(self):
        pass
    
    def test_schema_dict(self):
        sm = SchemaManager.from_filepath("./cornflow/schemas/pulp_json_schema.json")
        dict_schema = sm.jsonschema_to_dict()
        
        self.assertCountEqual(dict_schema["CoefficientSchema"], dict_example["CoefficientSchema"])
        self.assertCountEqual(dict_schema["ObjectiveSchema"], dict_example["ObjectiveSchema"])
        self.assertCountEqual(dict_schema["ConstraintsSchema"], dict_example["ConstraintsSchema"])
        self.assertCountEqual(dict_schema["VariablesSchema"], dict_example["VariablesSchema"])
        self.assertCountEqual(dict_schema["ParametersSchema"], dict_example["ParametersSchema"])
        self.assertCountEqual(dict_schema["Sos1Schema"], dict_example["Sos1Schema"])
        self.assertCountEqual(dict_schema["Sos2Schema"], dict_example["Sos2Schema"])
        self.assertCountEqual(dict_schema["DataSchema"], dict_example["DataSchema"])

    def test_flask_schema(self):
        # TODO: I am not sure how to test that
        pass
    
    def test_schema_validation(self):
        sm = SchemaManager.from_filepath("./cornflow/schemas/pulp_json_schema.json")
        val = sm.validate_file("./cornflow/tests/data/pulp_example_data.json")
        self.assertTrue(val)
    
    def test_validation_errors(self):
        sm = SchemaManager.from_filepath("./cornflow/schemas/pulp_json_schema.json")
        data1 = {"objective": [], "constraints": [], "variables": []}
        data2 = {"objective": [], "constraints": ["notAConstraint"], "variables": ["notAVariable"]}
        bool1 = sm.validate_data(data1)
        val1 = sm.get_validation_errors(data1)
        val2 = sm.get_validation_errors(data2)
        self.assertFalse(bool1)
        self.assertEqual(len(val1), 1)
        self.assertEqual(val1[0].message, "[] is not of type 'object'")
        self.assertEqual(len(val2), 3)
    
    
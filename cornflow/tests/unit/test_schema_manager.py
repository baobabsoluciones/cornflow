from cornflow.schemas.schema_manager import SchemaManager
from unittest import TestCase
from cornflow.tests.data.dict_schema_example import dict_example
from cornflow.schemas.constants import DATASCHEMA


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
        self.assertCountEqual(dict_schema[DATASCHEMA], dict_example[DATASCHEMA])

    def test_flask_schema(self):
        # TODO: I am not sure how to test that
        pass
    
    def test_schema_validation(self):
        sm = SchemaManager.from_filepath("./cornflow/schemas/pulp_json_schema.json")
        val = sm.validate_file("./cornflow/tests/data/pulp_example_data.json")
        self.assertTrue(val)

    def test_schema_validation_2(self):
        sm = SchemaManager.from_filepath("./cornflow/tests/data/data_schema.json")
        val = sm.validate_file("./cornflow/tests/data/data_input.json")
        
        # Test that it can be transformed into a dict
        dict_schema = sm.jsonschema_to_dict()
        self.assertTrue(val)
    
    def test_validation_errors(self):
        sm = SchemaManager.from_filepath("./cornflow/schemas/pulp_json_schema.json")
        data = {"objective": [], "constraints": [], "variables": []}
        bool = sm.validate_data(data)
        val = sm.get_validation_errors(data)
        self.assertFalse(bool)
        self.assertEqual(len(val), 1)
        self.assertEqual(val[0].message, "[] is not of type 'object'")
    
    def test_validation_errors2(self):
        sm = SchemaManager.from_filepath("./cornflow/schemas/pulp_json_schema.json")
        data = {"objective": [], "constraints": ["notAConstraint"], "variables": ["notAVariable"]}
        val = sm.get_validation_errors(data)
        self.assertEqual(len(val), 3)

    def test_validation_errors3(self):
        sm = SchemaManager.from_filepath("./cornflow/tests/data/data_schema.json")
        bool = sm.validate_file("./cornflow/tests/data/data_input_bad.json")
        val = sm.get_file_errors("./cornflow/tests/data/data_input_bad.json")
        self.assertFalse(bool)
        self.assertEqual(len(val), 2)
     
    def test_schema_names(self):
        sm = SchemaManager.from_filepath("./cornflow/tests/data/name_problem_schema.json")
        dict_schema = sm.jsonschema_to_dict()
        self.assertEqual(len(dict_schema["CoefficientsSchema"]), 2)
        self.assertEqual(len(dict_schema["Coefficients1Schema"]), 1)
      
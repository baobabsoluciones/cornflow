"""

"""
import json
import os
import pickle
from unittest import TestCase

from cornflow_client import InstanceCore

from cornflow_client.schema.tools import get_empty_schema


# Constants
path_to_tests_dir = os.path.dirname(os.path.abspath(__file__))

# Helper functions
def _load_file(_file):
    with open(_file) as f:
        temp = json.load(f)
    return temp


def _get_file(relative_path):
    return os.path.join(path_to_tests_dir, relative_path)


class TestSimpleApplicationDag(TestCase):
    def setUp(self):
        self.class_to_use = SimpleInstance
        self.instance_filename = _get_file("../data/gc_input.json")
        self.instance_data = _load_file(self.instance_filename)
        self.schema = get_empty_schema()

    def tearDown(self):
        pass

    def test_instance_from_dict(self):
        instance = self.class_to_use.from_dict(self.instance_data)
        self.assertEqual(self.instance_data, instance.data)
        return instance

    def test_instance_to_dict(self):
        instance = self.test_instance_from_dict()
        self.assertEqual(self.instance_data, instance.to_dict())

    def test_instance_from_json(self):
        instance = self.class_to_use.from_json(self.instance_filename)
        self.assertEqual(self.instance_data, instance.data)
        return instance

    def test_instance_to_json(self):
        instance = self.test_instance_from_json()
        instance.to_json(_get_file("../data/gc_input_export.json"))
        read_data = _load_file(_get_file("../data/gc_input.json"))
        self.assertEqual(self.instance_data, read_data)
        os.remove(_get_file("../data/gc_input_export.json"))

    def test_instance_schema(self):
        instance = self.test_instance_from_dict()
        self.assertEqual(self.schema, instance.schema)

    def test_schema_validation(self):
        instance = self.test_instance_from_dict()
        self.assertEqual([], instance.check_schema())

    def test_schema_generation(self):
        instance = self.test_instance_from_dict()
        schema = _load_file(_get_file("../data/graph_coloring_input.json"))
        schema["properties"]["pairs"].pop("description")
        self.assertEqual(schema, instance.generate_schema())

    def test_to_excel(self):
        instance = self.test_instance_from_dict()
        instance.to_excel(_get_file("../data/gc_input_export.xlsx"))
        instance_2 = self.class_to_use.from_excel(
            _get_file("../data/gc_input_export.xlsx")
        )
        self.assertEqual(instance.data, instance_2.data)
        os.remove(_get_file("../data/gc_input_export.xlsx"))


class TestCustomInstanceDag(TestSimpleApplicationDag):
    def setUp(self):
        super().setUp()
        self.class_to_use = Instance
        self.schema = _load_file(_get_file("../data/graph_coloring_input.json"))

    def test_instance_from_dict(self):
        """Here as to be not equal as the data has been processed on the from_dict method"""
        instance = self.class_to_use.from_dict(self.instance_data)
        self.assertNotEqual(self.instance_data, instance.data)
        return instance

    def test_instance_from_json(self):
        """Here as to be not equal as the data has been processed on the from_dict method"""
        instance = self.class_to_use.from_json(self.instance_filename)
        self.assertNotEqual(self.instance_data, instance.data)
        return instance


class SimpleInstance(InstanceCore):
    schema = get_empty_schema()
    schema_checks = get_empty_schema()


class Instance(InstanceCore):
    schema = _load_file(_get_file("../data/graph_coloring_input.json"))
    schema_checks = get_empty_schema()

    @classmethod
    def from_dict(cls, data):
        tables = ["pairs"]

        data_p = {el: {(v["n1"], v["n2"]): v for v in data[el]} for el in tables}

        return cls(data_p)

    def to_dict(self):
        tables = ["pairs"]

        data_p = {el: self.data[el].values_l() for el in tables}
        return pickle.loads(pickle.dumps(data_p, -1))

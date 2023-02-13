import json
import os
from unittest import TestCase
from cornflow_client.schema.tools import schema_from_excel
from cornflow_client.core.tools import load_json


class TestSchemaFromExcel(TestCase):
    def setUp(self) -> None:
        self.root_data = os.path.join(os.path.dirname(__file__), "../data")
        self.xl_with_fk = self.get_data_file("xl_with_fk.xlsx")
        self.xl_without_fk = self.get_data_file("xl_without_fk.xlsx")
        self.xl_with_methods = self.get_data_file("xl_with_methods.xlsx")
        self.xl_with_access = self.get_data_file("xl_with_access.xlsx")
        self.schema_with_fk = self.get_data_file("schema_with_fk.json")
        self.schema_without_fk = self.get_data_file("schema_without_fk.json")
        self.endpoints_methods = self.get_data_file("endpoints_methods.json")
        self.endpoints_access = self.get_data_file("endpoints_access.json")

    def get_data_file(self, filename):
        return os.path.join(self.root_data, filename)

    def test_schema_with_fk(self):
        schema, methods, access = schema_from_excel(self.xl_with_fk, fk=True)
        expected = load_json(self.schema_with_fk)
        self.assertEqual(schema, expected)

    def test_schema_without_fk(self):
        schema, methods, access = schema_from_excel(self.xl_without_fk, fk=False)
        expected = load_json(self.schema_without_fk)
        self.assertEqual(schema, expected)

    def test_endpoints_methods(self):
        schema, methods, access = schema_from_excel(self.xl_with_methods, fk=True)
        expected = load_json(self.endpoints_methods)
        self.assertEqual(methods, expected)

    def test_endpoints_access(self):
        schema, methods, access = schema_from_excel(self.xl_with_access, fk=True)
        expected = load_json(self.endpoints_access)
        self.assertEqual(access, expected)
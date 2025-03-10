import os
from cornflow_client import InstanceCore, get_empty_schema
from cornflow_client.core.tools import load_json
import pytups as pt


class Instance(InstanceCore):
    schema = load_json(os.path.join(os.path.dirname(__file__), "../schemas/input.json"))
    schema_checks = get_empty_schema()

    def get_pairs(self):
        return pt.TupList((el["n1"], el["n2"]) for el in self.data["pairs"])

from .cornflow_client import CornFlow, group_variables_by_name, CornFlowApiError
from .schema_manager import SchemaManager
import json
import os


def get_pulp_jsonschema():
    filename = os.path.join(os.path.dirname(__file__), 'data', "pulp_json_schema.json")
    with open(filename, 'r') as f:
        content = json.load(f)
    return content
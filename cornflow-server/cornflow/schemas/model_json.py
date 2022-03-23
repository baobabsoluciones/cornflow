from cornflow_client import SchemaManager, get_pulp_jsonschema
import os

fileDir = os.path.dirname(__file__)

manager = SchemaManager(get_pulp_jsonschema())

DataSchema = manager.jsonschema_to_flask()

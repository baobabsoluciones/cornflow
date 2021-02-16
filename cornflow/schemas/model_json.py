from .schema_manager import SchemaManager
import os

fileDir = os.path.dirname(os.path.realpath(__file__))

manager = SchemaManager.from_filepath("./json_schemas/pulp_json_schema.json")

DataSchema = manager.jsonschema_to_flask()

from cornflow_client import SchemaManager
import os

fileDir = os.path.dirname(__file__)
filePath = os.path.join(fileDir, '..', 'static', 'pulp_json_schema.json')
manager = SchemaManager.from_filepath(filePath)

DataSchema = manager.jsonschema_to_flask()

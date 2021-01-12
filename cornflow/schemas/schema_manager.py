import json
from jsonschema import validate



class SchemaManager:
    
    def __init__(self, schema_path=None):
        if schema_path is not None:
            self.load_schema(schema_path)
        
    def load_json(self, path):
        with open(path) as json_file:
            file = json.load(json_file)
        return file
    
    def load_schema(self, path):
        self.jsonschema = self.load_json(path)
        
    def validate_data(self, data_path):
        data = self.load_json(data_path)
        try:
            validate(data, self.jsonschema)
            return True
        except:
            print("json file not valid")
            return False
    
    def schema_to_dict(self):
        pass
    
    def schema_to_flask(self):
        pass
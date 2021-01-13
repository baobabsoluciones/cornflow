import json
import re
from jsonschema import validate



class SchemaManager:
    
    def __init__(self, schema_path=None):
        if schema_path is not None:
            self.load_schema(schema_path)
        
        self.types = {"string": "String", "number": "Float", "integer": "Integer", "null": None}
        self.schema_dict = {"DataSchema": {}}
        
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
    
        self.schema_dict = {"DataSchema": {}}

        for item in self.jsonschema["definitions"].items():
            self.get_element_dict(item)
        
        for item in self.jsonschema["properties"].items():
            self.get_element_dict(item)
            self.create_data_schema(item)

        print(self.schema_dict)
        return self.schema_dict

    def create_data_schema(self, item):
        name = item[0]
        content = item[1]

        schema = dict(name=name,
                    type=self.get_schema_name(name),
                    many=("type" in content and content["type"]=="array"),
                    required=True)
        self.schema_dict["DataSchema"].update(schema)
        
        return schema
    
    def schema_to_flask(self):
        pass
    
    def get_element_dict(self, item, required_list=None):
        print(item)
        if required_list==None:
            required_list = []
        
        name = item[0]
        content = item[1]
        if "type" not in content:
            if "$ref" in content:
                return {
                    "name": name,
                    "type": self.get_ref(item),
                    "many": False,
                    "required": (name in required_list)
                }
        if content["type"] == "object":
            return {
                "name": name,
                "type": self.get_object_schema(item),
                "many": False,
                "required": (name in required_list)
            }
        elif content["type"] == "array":
            return {
                "name": name,
                "type": self.get_array_schema(item),
                "many": True,
                "required": (name in required_list)
            }
        else:
            return self.get_item_dict(item, required_list)
    
    def get_object_schema(self, item):
        name = item[0]
        content = item[1]
        schema_name = self.get_schema_name(name)
        self.schema_dict.update(
            {schema_name: [self.get_element_dict(i, self.get_required(content)) for i in content["properties"].items()]}
        )
        return schema_name
    
    def get_array_schema(self, item):
        name = item[0]
        content = item[1]["items"]
        schema_name = self.get_schema_name(name)
        if "type" in content and content["type"] == "object":
            self.schema_dict.update(
                {schema_name: [self.get_element_dict(i, self.get_required(content)) for i in content["properties"].items()]}
            )
        elif "$ref" in content:
            schema_name = self.get_ref((None, content))
        else:
            self.schema_dict.update({schema_name: [self.get_element_dict(i, self.get_required(content)) for i in content.items()]})
        return schema_name
        
    def get_item_dict(self, item, required_list=None):
        
        d = dict(
            name=item[0],
            type=self.get_type(item[1]["type"]),
            required=(item[0] in required_list),
            allow_none=("null" in item[1]["type"]),
            many=False)
        return d
    
    def get_ref(self, item):
        content = item[1]
        ref = re.search("definitions\\/(.+)", content["$ref"]).group(1)
        return self.get_schema_name(ref)
    
    def get_type(self, json_type):
        if type(json_type) is list:
            if "null" in json_type:
                json_type.remove("null")
            if len(json_type) > 1:
                raise Warning("Warning: more than one type given")
            return self.types[json_type[0]]
        else:
            return self.types[json_type]
    
    def get_ref_dict(self):
        pass
    
    def get_schema_name(self, name):
        return name.capitalize() + "Schema"
    
    def get_required(self, content):
        if "required" in content:
            return content["required"]
        else:
            return []
        
    
    def print_dict(self, path):
        with open(path, 'w') as outfile:
            json.dump(self.schema_dict, outfile)
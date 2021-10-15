import json
import os


def get_pulp_jsonschema(filename="pulp_json_schema.json", path="data"):
    """
    returns the PuLP model schema
    """
    filename = os.path.join(os.path.dirname(__file__), "..", path, filename)
    with open(filename, "r") as f:
        content = json.load(f)
    return content


def get_empty_schema(properties=None, solvers=None):
    """
    assumes the first solver is the default
    """
    schema = get_pulp_jsonschema("empty_schema.json")
    if properties is not None:
        schema["properties"] = properties
    if solvers is not None:
        schema["properties"]["solver"] = dict(
            type="string", enum=solvers, default=solvers[0]
        )
    return schema

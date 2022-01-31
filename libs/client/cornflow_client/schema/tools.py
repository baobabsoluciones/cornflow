"""

"""
# Full imports
import json
import os

# Imports from internal modules
from cornflow_client.core import InstanceSolutionCore
from cornflow_client.core.read_tools import read_excel


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


def schema_from_excel(path_in, param_tables=None, path_out=None):
    """
    Create a jsonschema based on an excel data file.

    :param path_in: path of the excel file
    :param param_tables: array containing the names of the parameter tables
    :param path_out: path where to save the json schema as a json file.
    :return: the jsonschema
    """
    if not param_tables:
        param_tables = []
    xl_data = read_excel(path_in, param_tables)
    data = {k: str_columns(v) if isinstance(v, list) else v for k, v in xl_data.items()}

    class InstSol(InstanceSolutionCore):
        schema = {}

    instance = InstSol(data)
    schema = instance.generate_schema()

    if path_out is not None:
        with open(path_out, "w") as f:
            json.dump(schema, f, indent=4, sort_keys=False)

    return schema


def str_key(dic):
    """
    Apply str to the keys of a dict.
    This must be a applied to a dict in order to transform it into json.

    :param dic: a dict
    :return: the dict with keys as strings.
    """
    return {str(k): v for k, v in dic.items()}


def str_columns(table):
    """
    Transform the columns of a table (the keys of a list of dict) into strings.

    :param table: a list of dict.
    :return: the modified list of dict
    """
    return [str_key(d) for d in table]

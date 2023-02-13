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


def clean_none(dic):
    """
    Remove empty values from a dict

    :param dic: a dict
    :return: the filtered dict
    """
    remove = ["NaT", "NaN", None]
    return {k: v for k, v in dic.items() if not v in remove}


def check_fk(fk_dic):
    """
    Check the format of foreign keys

    :param fk_dic: a dict of foreign keys values
    :return: None (raise an error if problems are detected)
    """
    problems = []
    for table, fk in fk_dic.items():
        for k, v in fk.items():
            if "." not in v:
                problems += [(table, k, v)]
    if len(problems):
        message = (
            f'Foreign key format should be "table.key". '
            f"Problem detected for the following table, keys and values: {problems}"
        )
        raise ValueError(message)


def schema_from_excel(
    path_in,
    param_tables=None,
    path_out=None,
    fk=False,
    path_methods=None,
    path_access=None,
):
    """
    Create a jsonschema based on an Excel data file.

    :param path_in: path of the Excel file
    :param param_tables: array containing the names of the parameter tables
    :param path_out: path where to save the json schema as a json file.
    :param fk: True if foreign key are described in the second line.
    :param path_methods: path where to save the methods dict as a json file
    :param path_access: path where to save the access dict as a json file
    :return: the jsonschema
    """
    if not param_tables:
        param_tables = []
    xl_data = read_excel(path_in, param_tables)

    # process and remove special tables
    if "endpoints_methods" in xl_data:
        endpoints_methods = {
            e["endpoint"]: [k for k, v in e.items() if v and k != "endpoint"]
            for e in xl_data["endpoints_methods"]
        }
        del xl_data["endpoints_methods"]
    else:
        endpoints_methods = None

    if "endpoints_access" in xl_data:
        endpoints_access = {
            e["endpoint"]: [k for k, v in e.items() if v and k != "endpoint"]
            for e in xl_data["endpoints_access"]
        }
        del xl_data["endpoints_access"]
    else:
        endpoints_access = None

    # process foreign keys
    if fk:
        fk_values = {
            k: clean_none(v[0]) for k, v in xl_data.items() if isinstance(v, list)
        }
        check_fk(fk_values)
        data = {
            k: str_columns(v[1:]) if isinstance(v, list) else v
            for k, v in xl_data.items()
        }
    else:
        fk_values = {}
        data = {
            k: str_columns(v) if isinstance(v, list) else v for k, v in xl_data.items()
        }

    # create the json schema
    class InstSol(InstanceSolutionCore):
        schema = {}

    instance = InstSol(data)
    schema = instance.generate_schema()
    for table, fk in fk_values.items():
        for k, v in fk.items():
            if v is not None:
                schema["properties"][table]["items"]["properties"][k].update(
                    {"foreign_key": v}
                )

    # Save json files
    if path_out is not None:
        with open(path_out, "w") as f:
            json.dump(schema, f, indent=4, sort_keys=False)
    if path_methods is not None:
        with open(path_methods, "w") as f:
            json.dump(endpoints_methods, f, indent=4, sort_keys=False)
    if path_access is not None:
        with open(path_access, "w") as f:
            json.dump(endpoints_access, f, indent=4, sort_keys=False)

    return schema, endpoints_methods, endpoints_access


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

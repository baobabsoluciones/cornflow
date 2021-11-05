from jsonschema import Draft7Validator
import json
import os


def load_schema(path):
    fd = open(path, "r")
    schema = json.load(fd)
    fd.close()
    return schema


cwd = os.path.dirname(os.path.realpath(__file__))
instance_schema = load_schema(os.path.join(cwd, "instance.json"))
solution_schema = load_schema(os.path.join(cwd, "solution.json"))


def check_schema(schema, data):
    checker = Draft7Validator(schema)
    if not checker.is_valid(data):
        raise ValueError("Data is not compatible with schema")
    return True


def check_instance(data):
    return check_schema(instance_schema, data)


def check_solution(data):
    return check_schema(solution_schema, data)

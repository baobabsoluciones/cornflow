import os, sys
from cornflow_client import ApplicationCore, InstanceCore, SolutionCore


class MyInstance(InstanceCore):
    schema = {
        "type": "object",
        "properties": {"field": {"type": ["string", "null", "number"]}},
        "required": ["field"],
    }
    schema_checks = {
        "type": "object",
        "properties": {},
        "required": [],
    }


class MySolution(SolutionCore):
    schema = {
        "type": "object",
        "properties": {"result": {"type": "string"}},
        "required": ["result"],
    }
    schema_checks = {
        "type": "object",
        "properties": {},
        "required": [],
    }


class TwoValidTypes(ApplicationCore):
    name = "app_test_various_types"
    instance = MyInstance
    solution = MySolution

    @property
    def schema(self):
        return {
            "type": "object",
            "properties": {
                "solver": {"enum": ["default"]},
                "timeLimit": {"type": "number"},
            },
            "required": ["solver", "timeLimit"],
        }

    @property
    def solvers(self):
        return {"default": None}

    @property
    def test_cases(self):
        return [
            {
                "name": "Field string valid",
                "instance": {"field": "texto"},
                "solution": {"result": "ok"},
                "description": "Field string valid",
            },
            {
                "name": "Field null valid",
                "instance": {"field": None},
                "solution": {"result": "ok"},
                "description": "Field null valid",
            },
            {
                "name": "Field number valid",
                "instance": {"field": 2},
                "solution": {"result": "ok"},
                "description": "Field number valid",
            },
        ]

    def solve(self, instance_data, config, solution_data=None):
        return (solution_data or {"result": "ok"}, {}, {}, [], {})

    def get_default_solver_name(self):
        return "default"

    def get_solver(self, name):
        class DummyExperiment:
            def __init__(self, inst, sol):
                self.schema_checks = {}

            def check_solution(self):
                return {}

            def get_objective(self):
                return 0

        return DummyExperiment

    def check_solution(self):
        return {}

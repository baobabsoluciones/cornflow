
from cornflow_client import ApplicationCore, InstanceCore, SolutionCore
from .test_dags import BaseDAGTests

class MyInstance(InstanceCore):
    schema = {
        "type": "object",
        "properties": {
            "campo": {"type": ["string", "null", "number"]}
        },
        "required": ["campo"],
    }
    schema_checks = {
        "type": "object",
        "properties": {},
        "required": [],
    }


class MySolution(SolutionCore):
    schema = {
        "type": "object",
        "properties": {
            "resultado": {"type": "string"}
        },
        "required": ["resultado"],
    }
    schema_checks = {
        "type": "object",
        "properties": {},
        "required": [],
    }


class AppTest(ApplicationCore):
    name = "app_test_various_types"
    instance = MyInstance
    solution = MySolution

    @property
    def schema(self):
        return {
            "type": "object",
            "properties": {
                "solver":    {"enum": ["default"]},
                "timeLimit": {"type": "number"},
            },
            "required": ["solver", "timeLimit"],
        }

    @property
    def solvers(self):
        # devolvemos un diccionario con una única clave "default".
        # El valor no importa realmente—solo para que ApplicationCore.get_solver
        # tenga algo en Self.solvers—, porque lo sobreescribimos en get_solver.
        return {"default": None}

    @property
    def test_cases(self):
        return [
            {
                "name": "Campo puede ser string o null",
                "instance": {"campo": "texto"},
                "solution": {"resultado": "ok"},
                "description": "Caso tipo múltiple",
            },
            {
                "name": "Campo null válido",
                "instance": {"campo": None},
                "solution": {"resultado": "ok"},
                "description": "Caso null permitido",
            },
            {
                "name": "Campo null válido",
                "instance": {"campo": 2},
                "solution": {"resultado": "ok"},
                "description": "Caso null permitido",
            },
        ]

    def solve(self, instance_data, config, solution_data=None):
        return (solution_data or {"resultado": "ok"}, {}, {}, [], {})

    def get_default_solver_name(self):
        return "default"

    def get_solver(self, name):
        """
        Debe devolver algo callable. Definimos aquí una clase mínima
        que tenga schema_checks, check_solution() y get_objective().
        """
        class DummyExperiment:
            def __init__(self, inst, sol):
                # inst es MyInstance(inst_data), sol es MySolution(sol_data)
                self.schema_checks = {}
            def check_solution(self):
                return {}
            def get_objective(self):
                return 0

        return DummyExperiment

    def check_solution(self):
        return {}


class TestVariousTypes(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        self.app = AppTest()
        # Añadimos "solver" para que _validate_config pase:
        self.config["solver"] = self.app.get_default_solver_name()
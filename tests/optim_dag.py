import unittest
from airflow_config.dags.model_functions import solve_model
from flaskr.schemas.solution_log import LogSchema
import json

class MyTestCase(unittest.TestCase):
    with open('gc_20_7.json', 'r') as f:
        data = json.load(f)

    config = dict(solver="CPLEX_CMD", timeLimit=10)

    def test_progress(self):
        solution, log, log_dict = solve_model(self.data, self.config)
        LS = LogSchema()
        LS.dump(log_dict)



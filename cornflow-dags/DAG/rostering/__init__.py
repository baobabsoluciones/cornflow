"""

"""

# Imports from libraries
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union

# Imports from cornflow libraries
from cornflow_client import ApplicationCore
from cornflow_client.core.tools import load_json

# Imports from internal modules
from .core import Instance, Solution
from .solvers import MipModel


class Rostering(ApplicationCore):
    name = "rostering"
    description = "Rostering model"
    instance = Instance
    solution = Solution
    solvers = dict(mip=MipModel)
    schema = load_json(os.path.join(os.path.dirname(__file__), "./schemas/config.json"))

    default_args = {
        "owner": "baobab",
        "depends_on_past": False,
        "start_date": datetime(2020, 2, 1),
        "email": [""],
        "email_on_failure": False,
        "email_on_retry": False,
        "schedule_interval": None,
    }

    extra_args = {"max_active_runs": 2}

    @property
    def test_cases(self) -> List[Union[Dict, Tuple[Dict, Dict]]]:
        # Base case with a split opening time on one day
        # no skills, no holidays, no downtime, no preferences
        data_1 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_1.json")
        )
        data_out1 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_solution_1.json")
        )

        # Base case with an employee downtime, no preferences, no skills, no holidays
        data_2 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_2.json")
        )

        # Base case with skills, no preferences, no holidays, no downtime, no skills
        data_3 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_3.json")
        )
        data_out3 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_solution_3.json")
        )

        # Base case with more opening hours to check the resting hours properly
        data_4 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_4.json")
        )

        # Base case with store and employee holidays, no downtime, no preferences, no skills
        data_5 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_5.json")
        )

        # Base case with preferences, skills, no holidays, no downtime
        data_7 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_7.json")
        )

        # Base case with everything but deactivated
        data_8 = load_json(
            os.path.join(os.path.dirname(__file__), "data/test_instance_8.json")
        )

        return [
            {
                "name": "Base case",
                "instance": data_1,
                "solution": data_out1,
                "description": "Base case with a split opening time on one day. "
                "No skills, no holidays, no downtime, no preferences",
            },
            {
                "name": "Employee downtime",
                "instance": data_2,
                "description": "Base case with an employee downtime, no preferences, no skills, no holidays",
            },
            {
                "name": "Employee skills",
                "instance": data_3,
                "solution": data_out3,
                "description": "Base case with skills, no preferences, no holidays, no downtime, no skills",
            },
            {
                "name": "Resting hours",
                "instance": data_4,
                "description": "Base case with more opening hours to check the resting hours properly",
            },
            {
                "name": "Store and employee holidays",
                "instance": data_5,
                "description": "Base case with store and employee holidays, no downtime, no preferences, no skills",
            },
            {
                "name": "Employee preferences",
                "instance": data_7,
                "description": "Base case with preferences, skills, no holidays, no downtime",
            },
            {
                "name": "Requirements deactivated",
                "instance": data_8,
                "description": "Base case with everything but deactivated",
            },
        ]

    def get_solver(self, name: str = "mip"):
        if "." in name:
            solver, _ = name.split(".")
        else:
            solver = name
        return self.solvers.get(solver)

import os

from cornflow_client import SolutionCore
from cornflow_client.core.tools import load_json


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution.json")
    )

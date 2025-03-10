# Imports from libraries
import os
from typing import Dict

# Imports from cornflow libraries
from cornflow_client import ExperimentCore
from cornflow_client.core.tools import load_json
from pytups import SuperDict, TupList

# Imports from internal modules
from .instance import Instance
from .solution import Solution


class Experiment(ExperimentCore):
    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution_checks.json")
    )

    def __init__(self, instance: Instance, solution: Solution = None) -> None:
        ExperimentCore.__init__(self, instance=instance, solution=solution)
        if solution is None:
            self.solution = Solution(
                SuperDict(
                    detail_cutting_patterns=SuperDict(),
                    number_cutting_patterns=SuperDict(),
                )
            )

    @property
    def instance(self) -> Instance:
        return self._instance

    @property
    def solution(self) -> Solution:
        return self._solution

    @solution.setter
    def solution(self, value: Solution) -> None:
        self._solution = value

    def solve(self, options: dict) -> dict:
        raise NotImplementedError()

    def get_objective(self) -> float:
        """Return the total loss of material"""
        # Total input material
        bar_length = self.instance.get_bars_length()
        number_bars_patterns = self.solution.get_number_bars_patterns()
        total_length_input_material = sum(
            [
                number_bars_patterns[(bar, pattern)] * bar_length[bar]
                for (bar, pattern) in number_bars_patterns.keys_tl()
            ]
        )
        # Total ouput material
        product_length = self.instance.get_product_length()
        demand = self.instance.get_demand()
        total_length_output_material = sum(
            [demand[product] * product_length[product] for product in demand.keys_tl()]
        )
        # Total loss of material
        return total_length_input_material - total_length_output_material

    def check_demand_satisfaction(self) -> TupList:
        """Checks demand satisfaction"""
        demand = self.instance.get_demand()
        total_number_cut_products = self.solution.get_total_number_cut_products()
        demand_satisfaction_problems = TupList(
            [
                {"id_product": product}
                for product in demand.keys_tl()
                if demand[product] != total_number_cut_products[product]
            ]
        )
        return demand_satisfaction_problems

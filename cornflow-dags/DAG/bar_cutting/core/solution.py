# Imports from libraries
import os
import pickle
from pytups import SuperDict, TupList

# Imports from cornflow libraries
from cornflow_client import SolutionCore
from cornflow_client.core.tools import load_json


class Solution(SolutionCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/output.json")
    )

    @classmethod
    def from_dict(cls, data: dict) -> "Solution":
        data_p = dict()
        data_p["detail_cutting_patterns"] = {
            (el["id_bar"], el["id_pattern"], el["id_product"]): el
            for el in data["detail_cutting_patterns"]
        }
        data_p["number_cutting_patterns"] = {
            (el["id_bar"], el["id_pattern"]): el
            for el in data["number_cutting_patterns"]
        }
        return cls(data_p)

    def to_dict(self) -> dict:
        tables = ["detail_cutting_patterns", "number_cutting_patterns"]
        data_p = {el: self.data[el].values_tl() for el in tables}
        return pickle.loads(pickle.dumps(data_p, -1))

    def _get_property(self, key, prop) -> SuperDict:
        return self.data[key].get_property(prop)

    def get_number_bars_patterns(self) -> SuperDict:
        """
        Returns a SuperDict with the ids of the bars and the patterns as keys and the number of patterns that should be cut as values.
        For example, {('bar1, 'pa2'): 1, ('bar1', 'pa3'): 200, ...}
        """
        return self._get_property("number_cutting_patterns", "number_of_patterns")

    def get_number_products_per_pattern(self) -> SuperDict:
        """
        Returns a SuperDict with the ids of the bars, the patterns and the products as keys and the number of products per bar and pattern as values.
        For example, {('bar1', 'pa2', 'pr1'): 0, ('bar1', 'pa2', 'pr2'): 2, ('bar1', 'pa2', 'pr3'): 0, ...}
        """
        return self._get_property("detail_cutting_patterns", "number_of_products")

    def get_total_number_cut_products(self) -> SuperDict:
        """
        Returns a SuperDict the products as keys and the total number of cut products as values.
        For example, {'pr1': 600, 'pr2': 500, ...}
        """
        number_patterns = self.get_number_bars_patterns()
        number_products_per_pattern = self.get_number_products_per_pattern()
        total_number_cut_products = SuperDict()
        for bar, pattern, product in number_products_per_pattern.keys_tl():
            if product not in total_number_cut_products.keys():
                total_number_cut_products[product] = (
                    number_products_per_pattern[(bar, pattern, product)]
                    * number_patterns[(bar, pattern)]
                )
            else:
                total_number_cut_products[product] += (
                    number_products_per_pattern[(bar, pattern, product)]
                    * number_patterns[(bar, pattern)]
                )
        return total_number_cut_products

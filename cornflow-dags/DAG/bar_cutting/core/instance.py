# Imports from libraries
import os
import pickle

# Imports from cornflow libraries
from cornflow_client import InstanceCore, get_empty_schema
from cornflow_client.core.tools import load_json
from pytups import SuperDict, TupList


class Instance(InstanceCore):
    schema = load_json(os.path.join(os.path.dirname(__file__), "../schemas/input.json"))
    schema_checks = get_empty_schema()

    @classmethod
    def from_dict(cls, data: dict) -> "Instance":
        tables = [
            "bars",
            "products",
            "demand",
        ]
        data_p = {el: {v["id"]: v for v in data[el]} for el in tables}
        data_p["cutting_patterns"] = {
            (el["id_bar"], el["id_pattern"], el["id_product"]): el
            for el in data["cutting_patterns"]
        }

        return cls(data_p)

    def to_dict(self) -> dict:
        tables = [
            "bars",
            "products",
            "demand",
            "cutting_patterns",
        ]
        data_p = {el: self.data[el].values_tl() for el in tables}

        return pickle.loads(pickle.dumps(data_p, -1))

    def get_bars(self) -> TupList:
        """
        Returns a TupList with the ids of the bars.
        For example, ['bar1', 'bar2', ...]
        """
        return self.data["bars"].keys_tl()

    def get_bar1_id(self) -> str:
        """
        Returns a string with the id of the bar1.
        For example, 'bar1'.
        """
        return self.get_bars()[0]

    def get_bar2_id(self) -> str:
        """
        Returns a string with the id of the bar1.
        For example, 'bar2'.
        """
        return self.get_bars()[1]

    def get_products(self) -> TupList:
        """
        Returns a TupList with the ids of the products.
        For example, ['pr1', 'pr2', ...]
        """
        return self.data["products"].keys_tl()

    def get_patterns(self) -> TupList:
        """
        Returns a TupList with the ids of the patterns.
        For example, ['pa1', 'pa2', ...]
        """
        return self.data["cutting_patterns"].keys_tl().take(1).unique()

    def get_bars_patterns(self) -> TupList:
        """
        Returns a TupList with combinations of bars and patterns.
        For example, [('bar1', 'pa1'), ('bar1', 'pa2'), ...]
        Here we use unique2 instead of unique to get a list of tuples instead of a list of lists.
        """
        return self.data["cutting_patterns"].keys_tl().take([0, 1]).unique2()

    def get_bars_patterns_products(self) -> TupList:
        """
        Returns a TupList with combinations of bars, patterns and products.
        For example, [('bar1', 'pa1', 'pr1'), ('bar1', 'pa1', 'pr2'), ...]
        """
        return self.data["cutting_patterns"].keys_tl()

    def _get_property(self, key, prop) -> SuperDict:
        return self.data[key].get_property(prop)

    def get_bars_length(self) -> SuperDict:
        """
        Returns a SuperDict with the bars as keys and the length of the bars as values.
        For example, {'bar1': 150, 'bar2': 200, ...}
        """
        return self._get_property("bars", "length")

    def get_bar1_length(self) -> int:
        """
        Returns an integer the length of the bar1.
        For example, 150.
        """
        id_bar1 = self.get_bar1_id()
        return self._get_property("bars", "length")[id_bar1]

    def get_bar2_length(self) -> int:
        """
        Returns an integer the length of the bar2.
        For example, 200.
        """
        id_bar2 = self.get_bar2_id()
        return self._get_property("bars", "length")[id_bar2]

    def get_product_length(self) -> SuperDict:
        """
        Returns a SuperDict with the products as keys and the length of the products as values.
        For example, {'pr1': 40, 'pr2': 60, ...}
        """
        return self._get_property("products", "length")

    def get_demand(self) -> SuperDict:
        """
        Returns a SuperDict with the products as keys and the demand per product as values.
        For example, {'pr1': 600, 'pr2': 500, ...}
        """
        return self._get_property("demand", "demand")

    def get_number_products_per_bar_pattern(self) -> SuperDict:
        """
        Returns a SuperDict with the bars, patterns and products as keys and the number of products per bar and pattern as values.
        For example, {('bar1', 'pa1', 'pr1'): 3, ('bar1', 'pa1', 'pr2'): 0, ...}
        """
        return self._get_property("cutting_patterns", "number_of_products")

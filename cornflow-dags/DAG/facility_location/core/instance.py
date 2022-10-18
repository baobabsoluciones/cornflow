from cornflow_client import InstanceCore, get_empty_schema
from cornflow_client.core.tools import load_json
import pandas as pd
import os
import pickle
from pytups import SuperDict


class Instance(InstanceCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/instance.json")
    )
    schema_checks = get_empty_schema()

    @classmethod
    def from_file(cls, path):
        data = SuperDict(
            suppliers=dict(sheet_name="suppliers_L1", index_col=[0, 1, 2]),
            products=dict(sheet_name="products", index_col=[0, 1, 2]),
            clients=dict(sheet_name="clients", index_col=[0, 1]),
            warehouses=dict(sheet_name="warehouses", index_col=[0, 1, 2, 3]),
            distances=dict(sheet_name="distances", index_col=[0, 1, 2]),
            restricted_flows=dict(sheet_name="not_allowed_flows", index_col=[0, 1]),
        )

        def read_table(**kwargs):
            return pd.read_excel(
                filename=path, header=0, **kwargs
            ).index.values.tolist()

        return cls(data.vapply(lambda v: read_table(**v)))

    @classmethod
    def from_dict(cls, data: dict) -> "Instance":
        tables = ["suppliers", "clients", "warehouses", "products"]
        data_p = {el: {v["id"]: v for v in data[el]} for el in tables}
        data_p["distances"] = {
            (el["origin"], el["destination"]): el for el in data["distances"]
        }
        data_p["restricted_flows"] = {
            (el["origin"], el["destination"]): el for el in data["restricted_flows"]
        }
        data_p["parameters"] = pickle.loads(pickle.dumps(data["parameters"], -1))
        return cls(data_p)

    def to_dict(self) -> dict:
        tables = [
            "suppliers",
            "clients",
            "warehouses",
            "products",
            "distances",
            "restricted_flows",
        ]
        data_p = {el: self.data[el].values_tl() for el in tables}
        data_p["parameters"] = self.data["parameters"]
        return pickle.loads(pickle.dumps(data_p, -1))

    def get_suppliers(self):
        return self.data["suppliers"].keys_tl()

    def get_clients(self):
        return self.data["clients"].keys_tl()

    def get_products(self):
        return self.data["products"].keys_tl()

    def get_warehouses(self):
        return self.data["warehouses"].keys_tl()

    def get_all_locations(self):
        return self.get_suppliers() + self.get_clients() + self.get_warehouses()

    def get_restricted_flows(self):
        return self.data["restricted_flows"].keys_tl()

    def _get_property(self, key, prop) -> SuperDict:
        return self.data[key].get_property(prop)

    def get_unit_cost(self):
        return self._get_property("products", "unit_cost")

    def get_nb_doses(self):
        return self._get_property("products", "nb_doses")

    def get_demand(self):
        return self._get_property("clients", "demand")

    def get_capacity(self):
        return self._get_property("warehouses", "capacity")

    def get_fixed_cost(self):
        return self._get_property("warehouses", "fixed_cost")

    def get_variable_cost(self):
        return self._get_property("warehouses", "variable_cost")

    def get_distances(self):
        return self._get_property("distances", "distance")

    def get_availability(self):
        return {
            (k, v["id_product"]): v["availability"]
            for k, v in self.data["suppliers"].items()
        }

    def get_unit_flow_cost(self):
        return self._get_property("distances", "distance").vapply(
            lambda v: v * self.data["parameters"]["cost_per_km_per_dose"]
        )

    def is_lower_level(self, iW1, iW2):
        levels = self._get_property("warehouses", "level")
        return levels[iW1] < levels[iW2]

    def is_higher_level(self, iW1, iW2):
        levels = self._get_property("warehouses", "level")
        return levels[iW1] > levels[iW2]

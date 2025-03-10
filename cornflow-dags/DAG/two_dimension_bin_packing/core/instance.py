import os
import random
import pickle
from datetime import datetime

from cornflow_client import InstanceCore
from cornflow_client.core.tools import load_json
from pytups import SuperDict


class Instance(InstanceCore):

    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/instance.json")
    )

    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/instance_checks.json")
    )

    @classmethod
    def from_dict(cls, data):
        data_p = dict()
        data_p["parameters"] = pickle.loads(pickle.dumps(data["parameters"], -1))
        data_p["items"] = {el["id"]: el for el in data["items"]}

        return cls(data_p)

    def to_dict(self):
        tables = ["items"]
        data_p = {el: self.data[el].values_l() for el in tables}
        data_p["parameters"] = self.data["parameters"]
        return pickle.loads(pickle.dumps(data_p, -1))

    def _get_property(self, key, prop) -> SuperDict:
        return self.data[key].get_property(prop)

    def get_items(self):
        return self.data["items"].keys_l()

    def get_x_axis(self):
        return [i for i in range(self.data["parameters"]["width"])]

    def get_y_axis(self):
        return [i for i in range(self.data["parameters"]["height"])]

    def get_items_value(self):
        return self._get_property("items", "value")

    def get_items_width(self):
        return self._get_property("items", "width")

    def get_items_height(self):
        return self._get_property("items", "height")

    def get_item_width(self, item):
        return self.data["items"][item]["width"]

    def get_item_height(self, item):
        return self.data["items"][item]["height"]

    def get_bin_width(self):
        return self.data["parameters"]["width"]

    def get_bin_height(self):
        return self.data["parameters"]["height"]

    def get_bin_area(self):
        return self.get_bin_width() * self.get_bin_height()

    def get_big_m(self):
        return self.get_bin_width() * self.get_bin_height()

    def get_cuts(self):
        total_item_area = sum(
            [
                self.get_item_width(item) * self.get_item_height(item)
                for item in self.get_items()
            ]
        )
        if total_item_area <= self.get_bin_area():
            print(f"No area valid cuts exist")
            return [], 0

        t = datetime.utcnow()
        cuts = {
            1: self.get_biggest_cut(),
            2: self.get_value_cut(),
            3: self.get_density_cut(),
        }
        cut = 4

        while True or cut < 1000:
            items = self.get_items()
            selection = set()
            while True:
                rand = random.randint(0, len(items) - 1)
                selection.add(items.pop(rand))
                area = sum(
                    [
                        self.get_item_width(item) * self.get_item_height(item)
                        for item in selection
                    ]
                )
                if area > self.get_bin_area():
                    break

            cuts[cut] = tuple(selection)
            cut += 1

            if (datetime.utcnow() - t).seconds > 3 or cut > 1000:
                break

        print(f"{cut - 1} cuts generated")
        return [i for i in cuts.keys()], cuts

    def get_biggest_cut(self):
        t = self.data["items"].values_l()
        items = []
        while True:
            biggest = max(t, key=lambda v: v["width"] * v["height"])
            t.remove(biggest)
            items.append(biggest)
            if sum([el["width"] * el["height"] for el in items]) > self.get_bin_area():
                break

        return tuple([el["id"] for el in items])

    def get_value_cut(self):
        t = self.data["items"].values_l()
        items = []
        while True:
            biggest = max(t, key=lambda v: v["value"])
            t.remove(biggest)
            items.append(biggest)
            if sum([el["width"] * el["height"] for el in items]) > self.get_bin_area():
                break

        return tuple([el["id"] for el in items])

    def get_density_cut(self):
        t = self.data["items"].values_l()
        items = []
        while True:
            biggest = max(t, key=lambda v: v["value"] / (v["width"] * v["height"]))
            t.remove(biggest)
            items.append(biggest)
            if sum([el["width"] * el["height"] for el in items]) > self.get_bin_area():
                break

        return tuple([el["id"] for el in items])

    def get_most_value_item(self):
        return max(
            self.data["items"].values_tl(),
            key=lambda v: v["value"] / (v["width"] * v["height"]),
        )["id"]

    def get_second_most_value(self):
        first = self.get_most_value_item()
        temp = SuperDict(self.data["items"])
        temp.pop(first)
        return max(
            temp.values_tl(), key=lambda v: v["value"] / (v["width"] * v["height"])
        )["id"]

    def check_non_valid_objects(self) -> list:
        items = list()
        for item in self.get_items():
            if (
                self.get_item_height(item) > self.get_bin_height()
                or self.get_item_width(item) > self.get_bin_height()
            ):
                items.append({"id": item})
        return items

    def check_non_valid_data(self) -> dict:
        valid = dict()
        non_valid = self.check_non_valid_objects()
        if len(non_valid) == len(self.get_items()):
            valid["valid"] = False
        return valid

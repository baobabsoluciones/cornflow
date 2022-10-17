from cornflow_client import InstanceCore, get_empty_schema
from cornflow_client.core.tools import load_json
import os


class Instance(InstanceCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/instance.json")
    )
    schema_checks = get_empty_schema()

    @classmethod
    def from_file(cls, path):
        with open(path, "r") as fd:
            lines = fd.readlines()

        first_line = lines[0]
        nb_objects, weight_capacity = first_line.replace("\n", "").split(" ")
        nb_objects = int(nb_objects)
        weight_capacity = int(weight_capacity)

        values = []
        weights = []
        for line in lines[1:]:
            values.append(int(line.replace("\n", "").split(" ")[0]))
            weights.append(int(line.replace("\n", "").split(" ")[1]))

        data = dict(
            values=values,
            weights=weights,
            weight_capacity=weight_capacity,
            nb_objects=nb_objects,
        )
        return cls(data)

    @classmethod
    def from_dict(cls, dict_data):
        data = dict()
        data["weight_capacity"] = dict_data["parameters"]["weight_capacity"]
        data["nb_objects"] = dict_data["parameters"]["nb_objects"]
        data["weights"] = []
        data["values"] = []
        data["ids"] = []
        for i in range(data["nb_objects"]):
            data["weights"].append(dict_data["objects"][i]["weight"])
            data["values"].append(dict_data["objects"][i]["value"])
            data["ids"].append(dict_data["objects"][i]["id"])

        return cls(data)

    def to_dict(self):

        data_dict = dict(parameters=dict(), objects=[])
        data_dict["parameters"]["weight_capacity"] = self.data["weight_capacity"]
        data_dict["parameters"]["nb_objects"] = self.data["nb_objects"]

        for i in range(self.data["nb_objects"]):
            weight = self.data["weights"][i]
            value = self.data["values"][i]
            data_dict["objects"].append(dict(weight=weight, value=value, id=i))

        return data_dict

    def get_objects_values(self):
        return {
            self.data["ids"][i]: self.data["values"][i]
            for i in range(self.get_number_objects())
        }

    def get_objects_weights(self):
        return {
            self.data["ids"][i]: self.data["weights"][i]
            for i in range(self.get_number_objects())
        }

    def get_weight_capacity(self):
        return self.data["weight_capacity"]

    def get_number_objects(self):
        return self.data["nb_objects"]

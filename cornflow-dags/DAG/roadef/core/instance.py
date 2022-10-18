from cornflow_client import InstanceCore, get_empty_schema
from cornflow_client.core.tools import load_json
import pickle
import xmltodict
import os
from pytups import SuperDict
from .tools import (
    _index,
    get_drivers,
    get_customers,
    get_sources,
    drivers_to_jsonschema,
    customers_to_jsonschema,
    sources_to_jsonschema,
    get_matrices_from_file,
    get_drivers_from_file,
    get_trailers_from_file,
    get_bases_from_file,
    get_sources_from_file,
    get_customers_from_file,
    copy,
)


class Instance(InstanceCore):
    schema = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/instance.json")
    )
    schema_checks = get_empty_schema()

    def __init__(self, data):
        super().__init__(data)
        self._id_trailers = self.data["trailers"].keys_tl()

    def copy(self):
        return Instance(copy(self.data))

    @classmethod
    def from_file(cls, path):
        with open(path, "r") as fd:
            data_file = xmltodict.parse(fd.read())

        data = data_file["IRP_Roadef_Challenge_Instance"].copy()
        data = cls.dict_to_int_or_float(data)

        matrices = get_matrices_from_file(data)
        drivers = get_drivers_from_file(data)
        trailers = get_trailers_from_file(data)
        bases = get_bases_from_file(data)
        sources = get_sources_from_file(data)
        customers = get_customers_from_file(data)

        data_out = dict(
            matrices=matrices,
            drivers=drivers,
            trailers=trailers,
            bases=bases,
            sources=sources,
            customers=customers,
            horizon=data["horizon"],
            unit=data["unit"],
        )

        return cls(data_out)

    @classmethod
    def from_dict(cls, data_dict):

        # main tables
        trailers = _index(data_dict["trailers"])
        drivers = get_drivers(data_dict)
        customers = get_customers(data_dict)
        sources = get_sources(data_dict)

        # dist and time matrices
        matrices = {(el["L1"], el["L2"]): el for el in data_dict["matrices"]}

        data_out = SuperDict(
            trailers=trailers,
            drivers=drivers,
            customers=customers,
            sources=sources,
            matrices=matrices,
            coordinates=data_dict.get("coordinates", []),
        )

        # other parameters
        for param in ["unit", "horizon"]:
            data_out[param] = data_dict["parameters"][param]

        data_out["bases"] = data_dict["bases"][0]
        return cls(data_out)

    def to_dict(self):
        data_dict = pickle.loads(pickle.dumps(self.data, -1))

        drivers_tables = drivers_to_jsonschema(data_dict["drivers"])
        customer_tables = customers_to_jsonschema(data_dict["customers"])
        sources_tables = sources_to_jsonschema(data_dict["sources"])

        result = SuperDict(
            {key: data_dict[key].values_tl() for key in ["trailers", "matrices"]}
        )

        result["parameters"] = dict(
            unit=data_dict["unit"], horizon=data_dict["horizon"]
        )
        result["bases"] = [data_dict["bases"]]
        result["coordinates"] = data_dict.get("coordinates", [])
        # we merge the allowedTrailers tables:
        for key in ["allowedTrailers"]:
            result[key] = sources_tables.pop(key) + customer_tables.pop(key)
        return (
            result._update(drivers_tables)
            ._update(customer_tables)
            ._update(sources_tables)
        )

    @staticmethod
    def dict_to_int_or_float(data_dict):
        """
        Tranforms a dictionary to change all strings into integer of floating numbers if the strings
            represent numbers
        For example: Transforms {a: '4', b: {c: '7', d: ['8.7', '9']}}
            into {a: 4, b: {c: 7, d: [8.7, 9]}}
        """
        for key in data_dict.keys():
            if isinstance(data_dict[key], str):
                if data_dict[key].isnumeric():
                    data_dict[key] = int(data_dict[key])
                else:
                    try:
                        fl = float(data_dict[key])
                        data_dict[key] = fl
                    except ValueError:
                        pass
            elif isinstance(data_dict[key], list):
                if isinstance(data_dict[key][0], str):
                    try:
                        data_dict[key] = list(map(int, data_dict[key]))
                    except ValueError:
                        try:
                            data_dict[key] = list(map(float, data_dict[key]))
                        except ValueError:
                            pass
                elif isinstance(data_dict[key][0], dict):
                    data_dict[key] = list(
                        map(Instance.dict_to_int_or_float, data_dict[key])
                    )
            elif isinstance(data_dict[key], dict):
                data_dict[key] = Instance.dict_to_int_or_float(data_dict[key])
        return dict(data_dict)

    @staticmethod
    def from_element_or_list_to_dict(element_or_list):
        """
        Converts a list into a dictionary indexed by the field 'index' of each element of the list.
        If the input is not a list, it is converted into a list before converting to a dictionary
        For example: [{'index': 4, 'value': 5}, {'index': 7, 'value': 8}]
            is transformed to {4: {'index': 4, 'value': 5}, 7: {'index': 7, 'value': 8}}
        """
        if not isinstance(element_or_list, list):
            element_or_list = [element_or_list]
        return {int(el["index"]): el for el in element_or_list}

    def get_number_customers(self):
        """Returns the total number of customers"""
        return len(self.data["customers"])

    def get_number_drivers(self):
        """Returns the total number of drivers"""
        return len(self.data["drivers"])

    def get_number_sources(self):
        """Returns the total number of sources"""
        return len(self.data["sources"])

    def get_number_locations(self):
        """Returns the total number of locations"""
        return len(self.data["sources"]) + len(self.data["customers"]) + 1

    def get_number_trailers(self):
        """Returns the total number of trailers"""
        return len(self.data["trailers"])

    def get_horizon(self):
        """Returns the total number of hours in the time horizon"""
        return self.data["horizon"]

    def get_unit(self):
        return self.data["unit"]

    def get_distance_between(self, point1, point2):
        """Returns the distance between two locations"""
        return self.data["matrices"][point1, point2]["dist"]

    def get_time_between(self, point1, point2):
        """Returns the travelling time between two locations"""
        return self.data["matrices"][point1, point2]["time"]

    def get_id_customers(self):
        """Returns the indices of all the customers"""
        return self.data["customers"].keys_tl()

    def get_id_sources(self):
        """Returns the indices of all the sources"""
        return self.data["sources"].keys_tl()

    def get_id_trailers(self):
        """Returns the indices of all the trailers"""
        return self._id_trailers

    def get_id_drivers(self):
        """Returns the indices of all the drivers"""
        return self.data["drivers"].keys_tl()

    def get_id_base(self):
        """Returns the index of the base"""
        return self.data["bases"]["index"]

    def get_customer(self, id_customer):
        """Returns the customer of given index"""
        return self.data["customers"][id_customer]

    def get_source(self, id_source):
        """Returns the source of given index"""
        return self.data["sources"][id_source]

    def get_driver(self, id_driver):
        """Returns the driver of given index"""
        return self.data["drivers"][id_driver]

    def get_trailer(self, id_trailer):
        """Returns the trailer of given index"""
        return self.data["trailers"][id_trailer]

    def get_property(self, key, prop):
        return self.data[key].get_property(prop)

    def get_trailer_property(self, id_trailer, prop):
        """Returns the property prop of the trailer of given index"""
        return self.data["trailers"][id_trailer][prop]

    def get_driver_property(self, id_driver, prop):
        """Returns the property prop of the driver of given index"""
        return self.data["drivers"][id_driver][prop]

    def get_customer_property(self, id_customer, prop):
        """Returns the property prop of the customer of given index"""
        return self.data["customers"][id_customer][prop]

    def get_source_property(self, id_source, prop):
        """Returns the property prop of the source of given index"""
        return self.data["sources"][id_source][prop]

    def get_location_property(self, id_location, prop):
        """
        Returns the property prop of the location of given index
        The location should be a customer of source
        """
        if self.is_source(id_location):
            return self.data["sources"][id_location][prop]
        elif self.is_customer(id_location):
            return self.data["customers"][id_location][prop]

    def is_call_in_customer(self, id_customer):
        """
        Returns True if the customer is a call-in customer
        """
        return self.get_location_property(id_customer, "callIn") == 1

    @staticmethod
    def is_base(location):
        """Returns True if the location is a base"""
        return location == 0

    def is_source(self, location):
        """Returns True if the location is a source"""
        return 0 < location < 1 + self.get_number_sources()

    def is_customer(self, location):
        """Returns True if the location is a customer"""
        return location >= 1 + self.get_number_sources()

    def is_valid_location(self, location):
        """
        Return True if the input is a valid location index
        """
        return (
            0 <= location < 1 + self.get_number_sources() + self.get_number_customers()
        )

    def is_customer_or_source(self, location):
        """Returns True if the location is customer or a source"""
        return self.is_customer(location) or self.is_source(location)

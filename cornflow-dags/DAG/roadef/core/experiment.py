from .solution import Solution
from .instance import Instance
from cornflow_client import ExperimentCore
from cornflow_client.core.tools import load_json
from pytups import SuperDict, TupList
from math import floor
import numpy as np
import os


class Experiment(ExperimentCore):
    schema_checks = load_json(
        os.path.join(os.path.dirname(__file__), "../schemas/solution_checks.json")
    )

    def __init__(self, instance, solution):
        if solution is None:
            solution = Solution(dict())
        super().__init__(instance, solution)
        self.horizon = self.instance.get_horizon()
        self.unit = self.instance.get_unit()
        self.nb_customers = self.instance.get_number_customers()
        self.nb_sources = self.instance.get_number_sources()
        self.nb_drivers = self.instance.get_number_drivers()
        self.nb_trailers = self.instance.get_number_trailers()

    @property
    def instance(self) -> Instance:
        return super().instance

    @property
    def solution(self) -> Solution:
        return super().solution

    @solution.setter
    def solution(self, value: Solution) -> None:
        self._solution = value

    def get_objective(self):
        return sum(
            self._get_shift_cost(shift) for shift in self.solution.get_all_shifts()
        )

    def get_aux_info_shift(self):
        """
        Returns a dictionary containing information about each shift of self.solution,
            like : the ending time of the shift (in minutes), the inventory of the trailer at the end of the shift,
            the total duration of the shift and its driving duration
            For example: {2: {'arrival_time': 367, 'final_inventory': 1760, 'duration': 187, 'driving_duration': 160},
                          3: {'arrival_time': 512, 'final_inventory': 950, 'duration': 203, 'driving_duration': 180} }
        """
        shifts = self.solution.get_shifts_dict()
        result = SuperDict()
        for id_shift, shift in shifts.items():
            cumulated_driving_time = 0
            for s, (stop, next_stop) in enumerate(
                zip(shift["route"], shift["route"][1:])
            ):
                stop["cumulated_driving_time"] = cumulated_driving_time
                cumulated_driving_time += self.instance.get_time_between(
                    stop["location"],
                    next_stop["location"],
                )
            shift["route"][-1]["cumulated_driving_time"] = cumulated_driving_time
            result[id_shift] = dict(
                arrival_time=shift["route"][-1]["arrival"],
                final_inventory=shift["initial_quantity"]
                + sum([step["quantity"] for step in shift["route"]]),
                duration=shift["route"][-1]["arrival"] - shift["departure_time"],
                driving_duration=sum(
                    self.instance.get_time_between(
                        stop["location"], next_stop["location"]
                    )
                    for stop, next_stop in zip(shift["route"], shift["route"][1:])
                ),
            )
        return result

    def _get_shift_cost(self, shift):
        """
        Calculates the cost of the given shift
        """
        total_cost = 0
        driver = shift["driver"]
        time_cost = self.instance.get_driver_property(driver, "TimeCost")
        layover_cost = self.instance.get_driver_property(driver, "LayoverCost")

        trailer = shift["trailer"]
        dist_cost = self.instance.get_trailer_property(trailer, "DistanceCost")

        current_stop = None
        layover = False

        for stop in shift["route"]:
            previous_stop = current_stop
            current_stop = stop["location"]
            if stop["layover_before"] == 1:
                layover = True
            if previous_stop is None:
                continue

            distance = self.instance.get_distance_between(previous_stop, current_stop)
            time = self.instance.get_time_between(previous_stop, current_stop)
            if self.is_customer_or_source(current_stop):
                time += self.instance.get_location_property(current_stop, "setupTime")
            total_cost += distance * dist_cost + time * time_cost

        if layover:
            total_cost += layover_cost
        return total_cost

    def calculate_inventories(self):
        """
        Calculates the inventory of each customer at each hour of the time horizon
        :return: A dictionary whose keys are the indexes of the customers
            and whose values are dictionaries containing two elements:
                - a list 'tank_quantity' containing the value of the inventory at each hour
                - an integer 'location' corresponding to the index of the customer
        For example: {2:  {'tank_inventory': [15000, 14000, 13000, 16000, ... , 14000, 13000], 'location': 2},
                      3:  {'tank_inventory': [4000, 4000, 4000, 1000, ..., 3000, 3000], 'location': 3}}
        """
        customers = self.instance.get_id_customers()
        _get_customer = lambda c, p: self.instance.get_location_property(c, p)
        # we need three things: consumption, initial stock and arrivals
        # we store each as a dictionary where each customer has a numpy array of length = horizon

        # 1. we get consumptions from forecasts
        consumption = (
            customers.to_dict(None)
            .vapply(_get_customer, "Forecast")
            .vapply(lambda v: -np.array(v))
            .vapply(lambda v: v[0 : self.horizon])
        )

        # 2. we get initial tanks and assign them to the first period
        initial_tank = consumption.vapply(lambda v: np.zeros(self.horizon))
        for k, v in initial_tank.items():
            v[0] = _get_customer(k, "InitialTankQuantity")

        # 3. we now use the solution to get the arrivals with routes
        shifts = self.solution.get_all_shifts()
        all_operations = TupList(
            operation for route_list in shifts.take("route") for operation in route_list
        )
        # for each route we take the location, the time and how much.
        # we only get customers and round the time and make positive the quantity
        arrivals_tup = (
            all_operations.take(["location", "arrival", "quantity"])
            .vfilter(lambda v: self.is_customer(v[0]))
            .vapply(lambda v: (v[0], floor(v[1] / self.unit), -round(v[2], 3)))
        )
        # we initialize at 0 and increase when a truck arrives:
        arrivals = consumption.vapply(lambda v: np.zeros(self.horizon))
        for customer, time, quantity in arrivals_tup:
            arrivals[customer][time] += quantity

        # we take advantage of both pytups broadcasting and numpys broadcasting
        # then we accumulate over periods
        stocks = (consumption + arrivals + initial_tank).vapply(np.cumsum)
        site_inventories = SuperDict()
        for _id, quantity_arr in stocks.items():
            site_inventories[_id] = dict(tank_quantity=quantity_arr, location=_id)
        return site_inventories

    # ====================================
    # ====================================
    # Verification of the solution

    def check_driver_and_trailer(self):
        check = TupList()
        for shift in self.solution.get_all_shifts():
            id_shift = shift.get("id_shift", None)
            driver = shift.get("driver", None)
            trailer = shift.get("trailer", None)

            if driver is None or trailer is None:
                dr_tr = dict(
                    id_shift=id_shift, missing_trailer=False, missing_driver=False
                )
                if driver is None:
                    dr_tr["missing_driver"] = True
                if trailer is None:
                    dr_tr["missing_trailer"] = True
                check.append(dr_tr)

        return check

    # Checks that the timeline is coherent for each shift
    def check_c02_timeline(self) -> TupList:
        """
        returns [{"id_shift": shift_id, "id_location": location}, ...] for incoherent
        timeline at given location
        """
        check = TupList()

        for shift in self.solution.get_all_shifts():
            driver = shift.get("driver", None)
            id_shift = shift.get("id_shift", None)
            if driver is None:
                continue

            last_point = self.instance.get_id_base()
            last_departure = shift["departure_time"]

            for operation in shift["route"]:
                current_point = operation["location"]
                travel_time = self.instance.get_time_between(last_point, current_point)
                layover_time = self.instance.get_driver_property(
                    driver, "LayoverDuration"
                )
                if (
                    operation["arrival"]
                    < last_departure
                    + travel_time
                    + operation["layover_before"] * layover_time
                ):
                    check.append({"id_shift": id_shift, "id_location": current_point})
                last_point = current_point
                last_departure = operation["departure"]
        return check

    # Checks the loading and delivery times
    def check_c03_wrong_index(self) -> TupList:
        """
        returns {"wrong_index": [{"id_shift": id_shift, "position": id_operation}, ... ]
          for non existent locations,

        """
        check = TupList()
        for shift in self.solution.get_all_shifts():
            id_shift = shift.get("id_shift", None)
            id_operation = 1

            for operation in shift["route"][:-1]:
                if not self.is_valid_location(operation["location"]):
                    check.append({"id_shift": id_shift, "position": id_operation})
                    continue

                location = operation["location"]
                if location > 0:
                    setup_time = self.instance.get_location_property(
                        location, "setupTime"
                    )
                    if operation["departure"] < operation["arrival"] + setup_time:

                        id_operation += 1

        return check

    def check_c03_setup_time(self) -> TupList:
        """
        returns [{"id_shift": id_shift, "id_location": location}, ...] for operation
        that does not respect setup time
        """
        check = TupList()
        for shift in self.solution.get_all_shifts():
            id_shift = shift.get("id_shift", None)
            id_operation = 1

            for operation in shift["route"][:-1]:
                if not self.is_valid_location(operation["location"]):
                    continue

                location = operation["location"]
                if location > 0:
                    setup_time = self.instance.get_location_property(
                        location, "setupTime"
                    )
                    if operation["departure"] < operation["arrival"] + setup_time:
                        check.append({"id_shift": id_shift, "id_location": location})
                        id_operation += 1

        return check

    # Checks that the operations are performed during customers'time windows
    def check_c_04_customer_TW(self):
        """
        returns [{"id_shift": shift_id, "id_location": location}, ... ] for operation out of customer's TW
        """
        check = TupList()

        for shift in self.solution.get_all_shifts():
            id_shift = shift.get("id_shift", None)

            for operation in shift["route"][:-1]:
                location = operation["location"]
                if not self.is_customer(location):
                    continue
                tw_found = False
                ind_tw = 0
                while (
                    ind_tw
                    < len(self.instance.get_customer_property(location, "timewindows"))
                    and not tw_found
                ):
                    time_window = self.instance.get_customer_property(
                        location, "timewindows"
                    )[ind_tw]
                    if (
                        time_window["start"] <= operation["arrival"]
                        and time_window["end"] >= operation["departure"]
                    ):
                        tw_found = True
                    ind_tw += 1
                if not tw_found:
                    check.append({"id_shift": id_shift, "id_location": location})
        return check

    # Checks that the loading and delivery sites are accessible for the vehicle
    def check_c_05_sites_accessible(self):
        """
        returns [{"id_shift": shift_id, "id_location": location, "id_trailer": trailer},
          ... ] for incompatible shift-location combination
        """
        check = TupList()
        for shift in self.solution.get_all_shifts():
            id_shift = shift.get("id_shift", None)
            trailer = shift.get("trailer", None)
            if trailer is None:
                continue

            for operation in shift["route"][:-1]:
                location = operation["location"]
                if self.is_customer_or_source(location):
                    if trailer not in self.instance.get_location_property(
                        location, "allowedTrailers"
                    ):
                        check.append(
                            {
                                "id_shift": id_shift,
                                "id_location": location,
                                "id_trailer": trailer,
                            }
                        )
        return check

    def check_c_0607_inventory_trailer_negative(self):
        check = TupList()
        last_trailer_quantity = [0] * len(self.instance.get_id_trailers())

        for trailer in self.instance.get_id_trailers():
            last_trailer_quantity[trailer] = self.instance.get_trailer_property(
                trailer, "InitialQuantity"
            )

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            driver = shift.get("driver", None)
            trailer = shift.get("trailer", None)

            id_shift = shift.get("id_shift", None)
            if driver is None or trailer is None:
                return check

            last_quantity = shift["initial_quantity"]

            for operation in shift["route"]:
                quantity = last_quantity + operation["quantity"]
                location = operation["location"]
                if round(quantity, 2) < 0:
                    check.append(
                        {
                            "id_shift": id_shift,
                            "id_location": location,
                            "quantity": quantity,
                        }
                    )

                last_quantity = quantity

            last_trailer_quantity[trailer] = last_quantity

        return check

    def check_c_0607_inventory_trailer_above_capacity(self):
        check = TupList()
        last_trailer_quantity = [0] * len(self.instance.get_id_trailers())

        for trailer in self.instance.get_id_trailers():
            last_trailer_quantity[trailer] = self.instance.get_trailer_property(
                trailer, "InitialQuantity"
            )

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            driver = shift.get("driver", None)
            trailer = shift.get("trailer", None)
            trailer_capacity = self.instance.get_trailer_property(trailer, "Capacity")
            id_shift = shift.get("id_shift", None)
            if driver is None or trailer is None:
                return check

            last_quantity = shift["initial_quantity"]

            for operation in shift["route"]:
                quantity = last_quantity + operation["quantity"]
                location = operation["location"]

                if round(quantity, 2) > trailer_capacity:
                    check.append(
                        {
                            "id_shift": id_shift,
                            "id_location": location,
                            "quantity": quantity,
                            "id_trailer": trailer,
                            "capacity": trailer_capacity,
                        }
                    )

                last_quantity = quantity

            last_trailer_quantity[trailer] = last_quantity

        return check

    def check_c_0607_inventory_trailer_final_inventory(self):
        check = TupList()
        last_trailer_quantity = [0] * len(self.instance.get_id_trailers())
        aux_info_shift = self.get_aux_info_shift()

        for trailer in self.instance.get_id_trailers():
            last_trailer_quantity[trailer] = self.instance.get_trailer_property(
                trailer, "InitialQuantity"
            )

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            driver = shift.get("driver", None)
            trailer = shift.get("trailer", None)

            id_shift = shift.get("id_shift", None)
            if driver is None or trailer is None:
                return check

            last_quantity = shift["initial_quantity"]

            for operation in shift["route"]:
                quantity = last_quantity + operation["quantity"]
                last_quantity = quantity

            if round(aux_info_shift[id_shift]["final_inventory"], 2) != round(
                last_quantity, 2
            ):
                check.append(
                    {
                        "id_shift": id_shift,
                        "final_inventory": round(
                            aux_info_shift[id_shift]["final_inventory"], 2
                        ),
                        "calculated_final_inventory": round(last_quantity, 2),
                    }
                )

            last_trailer_quantity[trailer] = last_quantity

        return check

    def check_c_0607_inventory_trailer_initial_inventory(self):
        check = TupList()
        last_trailer_quantity = [0] * len(self.instance.get_id_trailers())

        for trailer in self.instance.get_id_trailers():
            last_trailer_quantity[trailer] = self.instance.get_trailer_property(
                trailer, "InitialQuantity"
            )

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            driver = shift.get("driver", None)
            trailer = shift.get("trailer", None)

            id_shift = shift.get("id_shift", None)
            if driver is None or trailer is None:
                return check

            last_quantity = shift["initial_quantity"]

            for operation in shift["route"]:
                quantity = last_quantity + operation["quantity"]
                last_quantity = quantity

            if round(last_trailer_quantity[trailer], 2) != round(
                shift["initial_quantity"], 2
            ):
                check.append(
                    {
                        "id_shift": id_shift,
                        "initial_quantity": round(shift["initial_quantity"], 2),
                        "last_shift_final_inventory": round(
                            last_trailer_quantity[trailer], 2
                        ),
                        "id_trailer": trailer,
                    }
                )
            last_trailer_quantity[trailer] = last_quantity

        return check

    # Checks that the quantity delivered at a customer is positive and the quantity loaded at a source is also positive
    def check_c_11_quantity_delivered(self):
        """
        returns [{"id_shift": shift_id, "id_location": location, "quantity": quantity}, ... ] for operation with wrong sign
        """
        check = TupList()
        for shift in self.solution.get_all_shifts():
            id_shift = shift.get("id_shift", None)

            for i in range(1, len(shift["route"]) + 1):
                operation = shift["route"][i - 1]
                location = operation["location"]
                if self.is_source(location) and operation["quantity"] < 0:
                    check.append(
                        {
                            "id_shift": id_shift,
                            "id_location": location,
                            "quantity": operation["quantity"],
                        }
                    )
                elif self.is_customer(location) and operation["quantity"] > 0:
                    check.append(
                        {
                            "id_shift": id_shift,
                            "id_location": location,
                            "quantity": operation["quantity"],
                        }
                    )
        return check

    # For each delivery, the delivery must be smaller than the customer's tank's capacity
    def check_c_16_customer_tank_exceeds(self):
        check = TupList()
        for shift in self.solution.get_all_shifts():
            id_shift = shift.get("id_shift", None)

            for i in range(1, len(shift["route"]) + 1):
                operation = shift["route"][i - 1]
                location = operation["location"]

                if not self.is_customer(location):
                    continue

                call_in = self.instance.get_customer_property(location, "callIn")
                if call_in == 0:
                    capacity = self.instance.get_customer_property(location, "Capacity")

                    if -operation["quantity"] > capacity:
                        check.append(
                            {
                                "id_shift": id_shift,
                                "id_location": location,
                                "quantity": operation["quantity"],
                                "capacity": capacity,
                            }
                        )
        return check

    def check_c_16_customer_tank_too_low(self):
        check = TupList()
        for shift in self.solution.get_all_shifts():
            id_shift = shift.get("id_shift", None)

            for i in range(1, len(shift["route"]) + 1):
                operation = shift["route"][i - 1]
                location = operation["location"]

                if not self.is_customer(location):
                    continue

                call_in = self.instance.get_customer_property(location, "callIn")
                if call_in == 0:

                    min_ope_quantity = self.instance.get_customer(location).get(
                        "MinOperationQuantity", 0
                    )

                    if -operation["quantity"] < min_ope_quantity:
                        check.append(
                            {
                                "id_shift": id_shift,
                                "id_location": location,
                                "quantity": operation["quantity"],
                                "minimum_quantity": min_ope_quantity,
                            }
                        )

        return check

    # =================================
    # Verification of sites constraints
    def check_site_inventory_negative(self):
        check = TupList()
        operation_quantities = []

        for location in range(1 + self.nb_sources + self.nb_customers):
            operation_quantities.append([0] * self.horizon)

        site_inventories = self.calculate_inventories()
        for site_inventory in site_inventories.values():
            location = site_inventory["location"]
            if not self.is_valid_location(location):
                continue
            if location <= 1 + self.nb_sources:
                continue
            call_in = self.instance.get_customer_property(location, "callIn")
            if call_in == 1:
                continue
            for i in range(self.horizon):
                if round(site_inventory["tank_quantity"][i], 3) < 0:
                    check.append(
                        {
                            "id_location": location,
                            "hour": i,
                            "inventory": site_inventory["tank_quantity"][i],
                        }
                    )

        return check

    def check_site_inventory_exceeds(self):
        check = TupList()
        operation_quantities = []

        for location in range(1 + self.nb_sources + self.nb_customers):
            operation_quantities.append([0] * self.horizon)

        site_inventories = self.calculate_inventories()
        for site_inventory in site_inventories.values():
            location = site_inventory["location"]
            if not self.is_valid_location(location):
                continue
            if location <= 1 + self.nb_sources:
                continue
            call_in = self.instance.get_customer_property(location, "callIn")
            if call_in == 1:
                continue
            for i in range(self.horizon):
                if round(
                    site_inventory["tank_quantity"][i], 3
                ) > self.instance.get_customer_property(location, "Capacity"):
                    check.append(
                        {
                            "id_location": location,
                            "hour": i,
                            "inventory": site_inventory["tank_quantity"][i],
                            "capacity": self.instance.get_customer_property(
                                location, "Capacity"
                            ),
                        }
                    )

        return check

    def check_site_doesnt_exist(self):
        check = TupList()
        operation_quantities = []

        for location in range(1 + self.nb_sources + self.nb_customers):
            operation_quantities.append([0] * self.horizon)

        site_inventories = self.calculate_inventories()
        for site_inventory in site_inventories.values():
            location = site_inventory["location"]
            if not self.is_valid_location(location):
                check.append({"id_location": location})
                continue

        return check

    # =====================================
    # Verification of resources constraints
    def check_res_dr_01_intershift(self):
        """
        Check if drivers respect minimum inter-shift duration.

        returns: TupList [{"id_shift": id_shift, "id_driver": id_driver,
                         "duration": duration, "minimum_duration": minimum_duration,
                         "last_shift": id_last_shift}, ...]
                for drivers not respecting minInterShiftDuration
        """
        check = TupList()
        last_shift_driver = dict()
        end_of_last_shifts_drivers = [0] * self.nb_drivers
        aux_info_shift = self.get_aux_info_shift()

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            driver = shift.get("driver", None)
            id_shift = shift.get("id_shift", None)
            if driver is None:
                continue

            duration, min_duration = self.aux_check_resources_dr_01(
                shift, driver, end_of_last_shifts_drivers[driver]
            )
            if duration is not None:
                last_shift = last_shift_driver.get(driver)
                check.append(
                    {
                        "id_shift": id_shift,
                        "last_shift": last_shift,
                        "id_driver": driver,
                        "duration": duration,
                        "minimum_duration": min_duration,
                    }
                )

            last_shift_driver[driver] = id_shift
            end_of_last_shifts_drivers[driver] = aux_info_shift[id_shift][
                "arrival_time"
            ]

        return check

    def check_res_dr_03_max_duration(self):
        """
        Check if drivers respect maximum shift duration.

        returns: TupList [{"id_shift": id_shift, "id_driver": id_driver,
                         "duration": duration, "maximum_duration": maximum_duration}, ...]
                for drivers not respecting max shift duration
        """
        check = TupList()

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            driver = shift.get("driver", None)
            id_shift = shift.get("id_shift", None)
            if driver is None:
                continue

            duration, max_duration = self.aux_check_resources_dr_03(shift, driver)
            if duration is not None:
                check.append(
                    {
                        "id_shift": id_shift,
                        "id_driver": driver,
                        "duration": duration,
                        "maximum_duration": max_duration,
                    }
                )

        return check

    def check_res_dr_08_driver_TW(self):
        """
        Check if drivers respect their time windows.

        returns: TupList [{"id_shift": id_shift, "id_driver": id_driver}, ...]
                for drivers not respecting driver's time windows
        """
        check = TupList()

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            driver = shift.get("driver", None)
            id_shift = shift.get("id_shift", None)
            if driver is None:
                continue

            if self.aux_check_resources_dr_08(shift, id_shift, driver):
                check.append({"id_shift": id_shift, "id_driver": driver})

        return check

    def check_res_tl_01_shift_overlaps(self):
        """
        Check if trailers have overlapping shifts.

        returns: TupList [{"id_shift": id_shift, "last_shift": id_last_shift,
                         "id_trailer": id_trailer}, ...]
                for trailers having shifts that overlap
        """
        check = TupList()
        last_shift_trailer = dict()
        end_of_last_shifts_trailer = [0] * self.nb_trailers
        aux_info_shift = self.get_aux_info_shift()

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            trailer = shift.get("trailer", None)
            id_shift = shift.get("id_shift", None)
            if trailer is None:
                continue

            if self.aux_check_resources_tl_01(
                shift, end_of_last_shifts_trailer[trailer]
            ):
                last_shift = last_shift_trailer.get(trailer)
                check.append(
                    {
                        "id_shift": id_shift,
                        "last_shift": last_shift,
                        "id_trailer": trailer,
                    }
                )

            last_shift_trailer[trailer] = id_shift
            end_of_last_shifts_trailer[trailer] = aux_info_shift[id_shift][
                "arrival_time"
            ]

        return check

    def check_res_tl_03_compatibility_dr_tr(self):
        """
        Check if drivers and trailers are compatible.

        returns: TupList [{"id_shift": id_shift, "id_trailer": id_trailer,
                         "id_driver": id_driver}, ...]
                for shifts having drivers and trailers that are not compatibles
        """
        check = TupList()

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            driver = shift.get("driver", None)
            trailer = shift.get("trailer", None)
            id_shift = shift.get("id_shift", None)
            if driver is None or trailer is None:
                continue

            if self.aux_check_resources_tl_03(driver, trailer):
                check.append(
                    {"id_shift": id_shift, "id_trailer": trailer, "id_driver": driver}
                )

        return check

    def aux_check_resources_dr_01(self, shift, driver, end_of_last_shift):
        """
        returns True for shifts not respecting minInterShiftDuration
        """
        min_delay = self.instance.get_driver_property(driver, "minInterSHIFTDURATION")
        duration = shift["departure_time"] - end_of_last_shift
        if end_of_last_shift != 0 and duration < min_delay:
            return duration, min_delay
        return None, None

    # Checks that the shift respects maximum duration
    def aux_check_resources_dr_03(self, shift, driver):
        """
        returns driving_time for shifts not respecting mex driving duration
        """
        check = None
        max_driving_duration = self.instance.get_driver_property(
            driver, "maxDrivingDuration"
        )

        if shift["route"][0]["layover_before"] == 1:
            if shift["route"][0]["driving_time_before_layover"] > max_driving_duration:
                check = shift["route"][0]["driving_time_before_layover"]
        elif shift["route"][0]["cumulated_driving_time"] > max_driving_duration:
            check = shift["route"][0]["cumulated_driving_time"]

        for op in range(1, len(shift["route"])):
            if shift["route"][op]["layover_before"] == 1:
                if (
                    shift["route"][op - 1]["cumulated_driving_time"]
                    + shift["route"][op]["driving_time_before_layover"]
                    > driver["maxDrivingDuration"]
                ):
                    check = (
                        shift["route"][op - 1]["cumulated_driving_time"]
                        + shift["route"][op]["driving_time_before_layover"]
                    )
            elif shift["route"][op]["cumulated_driving_time"] > max_driving_duration:
                check = shift["route"][op]["cumulated_driving_time"]
        return check, max_driving_duration

    # Checks that the shift fits into the driver's time windows
    def aux_check_resources_dr_08(self, shift, id_shift, driver):
        """
        returns True for shifts not respecting drivers' TW
        """
        aux_info_shift = self.get_aux_info_shift()
        s = shift["departure_time"]
        e = aux_info_shift[id_shift]["arrival_time"]
        found = False
        i = 0
        while (
            i < len(self.instance.get_driver_property(driver, "timewindows"))
            and not found
        ):
            tw = self.instance.get_driver_property(driver, "timewindows")[i]
            if s >= tw["start"] and e <= tw["end"]:
                found = True
            i += 1
        return not found

    # Checks that two shifts with the same trailer do not overlap
    def aux_check_resources_tl_01(self, shift, end_of_last_shift):
        """
        returns True for shifts using the same trailer as other currently running shift
        """
        return end_of_last_shift != 0 and shift["departure_time"] < end_of_last_shift

    # Checks that the driver and the trailer and compatible
    def aux_check_resources_tl_03(self, driver, trailer):
        """
        returns True for incompatible driver-trailer combinations
        """
        return trailer not in self.instance.get_driver_property(driver, "trailer")

    # ===========================================
    # Verification of service quality constraints
    # Checks that all orders having a time window ending before the planning horizon are satisfied
    def check_qs_01_orders_satisfied(self):
        """
        returns [{"id_customer": id_customer, "num_order": num_order}, ... ] for not delivered orders
        """
        check = TupList()
        nb_missed_orders = 0
        orders_customers = []
        delivered_orders_customers = []

        for i in range(self.nb_customers):
            orders_customers.append([])
            delivered_orders_customers.append([])
        offset_customer = 1 + self.nb_sources

        for c in range(self.nb_customers):
            customer = self.instance.get_customer(c + offset_customer)
            if customer["callIn"] == 0 or customer["orders"] == []:
                continue
            orders_customers[c] = [0] * len(customer["orders"])
            delivered_orders_customers[c] = [0] * len(customer["orders"])

            for o in range(len(customer["orders"])):
                order = customer["orders"][o]
                if order["latestTime"] > self.horizon * self.unit:
                    orders_customers[c][o] = 0
                    delivered_orders_customers[c][o] = 0
                else:
                    orders_customers[c][o] = -1
                    delivered_orders_customers[c][o] = 0

        for shift in self.solution.get_all_shifts():
            for operation in shift["route"]:
                location = operation["location"]
                if location < 1 + self.nb_sources:
                    continue
                call_in = self.instance.get_customer_property(location, "callIn")
                orders = self.instance.get_customer_property(location, "orders")
                if call_in != 1 or not len(orders):
                    continue
                good_orders = (
                    TupList(orders)
                    .kvapply(lambda ord, order: (ord, order))
                    .vfilter(
                        lambda o: o[1]["earliestTime"]
                        <= operation[1]["arrival"]
                        <= o[1]["latestTime"]
                    )
                )

                for ord, order in good_orders:
                    delivered_orders_customers[location - offset_customer][ord] = (
                        delivered_orders_customers[location - offset_customer][ord]
                        + operation["quantity"]
                    )

        for c in range(self.nb_customers):
            customer = self.instance.get_customer(c + offset_customer)
            if not customer["orders"]:
                continue

            for o in range(len(customer["orders"])):
                quantity = customer["orders"][o]["Quantity"]
                flexibility = customer["orders"][o]["orderQuantityFlexibility"]
                if (
                    quantity * flexibility / 100
                    <= delivered_orders_customers[c][o]
                    <= quantity
                ):
                    orders_customers[c][o] = 1
                else:
                    check.append({"id_customer": c + offset_customer, "num_order": o})

        for c in range(self.nb_customers):
            customer = self.instance.get_customer(c + offset_customer)
            nb_missed_orders += sum(
                1
                for o in range(len(customer["orders"]))
                if orders_customers[c][o] == -1
                if customer["orders"]
            )

        return check

    # Checks that there are no run outs
    def check_qs_02_runouts(self):
        """
        returns [{"id_location": location, "nb_run_outs": nb_run_outs}, ... ] for locations experiencing run-outs
        """
        check = TupList()
        nb_run_outs = 0
        site_inventories = self.calculate_inventories()

        for site in site_inventories.keys():
            site_inventory = site_inventories[site]
            nb_inventory_run_out = 0
            if not site_inventories[site]:
                continue
            if site > self.nb_customers + self.nb_sources + 1:
                continue
            if self.is_customer(site):
                customer = self.instance.get_customer(site)
                nb_inventory_run_out += sum(
                    1
                    for i in range(self.horizon)
                    if round(site_inventory["tank_quantity"][i], 2) < 0
                    if customer["callIn"] == 0
                )
            nb_run_outs += nb_inventory_run_out
            if nb_inventory_run_out != 0:
                check.append({"id_location": site, "nb_run_outs": nb_inventory_run_out})
        return check

    # Checks that callIn customers only receive deliveries linked to an order
    def check_qs_03_callins(self):
        check = TupList()
        for shift in self.solution.get_all_shifts():
            id_shift = shift["id_shift"]
            check += self.sub_check_qs_03(shift, id_shift)
        return check

    # Checks that the shift's operations on callIn customers are related to an order
    def sub_check_qs_03(self, shift, id_shift):
        """
        returns [{"id_shift": shift_id, "id_location": location}, ... ] for deliveries not related to an order to callIn customer
        """
        check = TupList()

        for operation in shift["route"][:-1]:
            location = operation["location"]
            if not self.is_valid_location(location):
                continue
            if not self.is_customer(location):
                continue
            customer = self.instance.get_customer(location)
            if customer["callIn"] == 0 or not customer["orders"]:
                continue
            tw_found = False
            ind_tw = 0
            while ind_tw < len(customer["orders"]) and not tw_found:
                order = customer["order"][ind_tw]
                if order["earliestTime"] <= operation["arrival"] <= order["latestTime"]:
                    tw_found = True
                ind_tw += 1
            if not tw_found:
                check.append({"id_shift": id_shift, "id_location": location})
        return check

    def generate_log(self, check_dict):
        """
        Transforms the dictionary returned by check_solution into a string log
        """
        check_log = ""

        # Shifts
        for row in check_dict.get("driver_and_trailer", []):
            check_log += f"Shift : {row['id_shift']} has no driver or no trailer.\n"

        for row in check_dict.get("c_02_timeline", []):
            check_log += f"check_shift_02, shift {row['id_shift']}. "
            check_log += (
                f"Operation at location {row['id_location']} arrives too early.\n"
            )
        for row in check_dict.get("c_03_wrong_index", []):
            check_log += f"check_shift_03, shift {row['id_shift']}. "
            check_log += f"Operation nº{row['position']} has a wrong location index.\n"

        for row in check_dict.get("c_03_setup_times", []):
            check_log += f"check_shift_03, shift {row['id_shift']}. "
            check_log += f"Departure of operation at location {row['id_location']} is too early.\n"

        for row in check_dict.get("c_04_customer_TW", []):
            check_log += f"check_shift_04, shift {row['id_shift']}. "
            check_log += f"Operation at location {row['id_location']} is out of the time windows.\n"

        for row in check_dict.get("c_05_sites_accessible", []):
            check_log += f"check_shift_05, shift {row['id_shift']}. "
            check_log += f"Operation at location {row['id_location']} can't accept this trailer.\n"

        for row in check_dict.get("c_0607_inventory_trailer_negative", []):
            check_log += f"check_shift_06, shift {row['id_shift']}. "
            check_log += f"Operation at location {row['id_location']} makes the trailer's inventory negative.\n"

        for row in check_dict.get("c_0607_inventory_trailer_above_capacity", []):
            check_log += f"check_shift_06, shift {row['id_shift']}. "
            check_log += f"Operation at location {row['id_location']} makes the trailer's inventory above its capacity.\n"

        for row in check_dict.get("c_0607_inventory_trailer_final_inventory", []):
            check_log += f"check_shift_07, shift {row['id_shift']}. "
            check_log += (
                f"The trailer's operations do not correspond to its final inventory.\n"
            )

        for row in check_dict.get("c_0607_inventory_trailer_initial_inventory", []):
            check_log += f"check_shift_07, shift {row['id_shift']}. "
            check_log += f"The initial inventory is not coherent with last shift of the trailer.\n"

        for row in check_dict.get("c_11_quantity_delivered", []):
            check_log += f"check_shift_11, shift {row['id_shift']}. "
            check_log += f"Operation at location {row['id_location']} has wrong sign.\n"

        for row in check_dict.get("c_16_customer_tank_exceeds", []):
            check_log += f"check_shift_16, shift {row['id_shift']}. "
            check_log += f"Operation at customer {row['id_location']} has quantity higher than tank's capacity.\n"

        for row in check_dict.get("c_16_customer_tank_too_low", []):
            check_log += f"check_shift_16, shift {row['id_shift']}. "
            check_log += f"Operation at customer {row['id_location']} has quantity lower than minimum quantity.\n"

        # Sites
        for row in check_dict.get("site_inventory_negative", []):
            check_log += f"check_sites, site_inventory {row['id_location']}. "
            check_log += f"Tank quantity strictly negative  at hour {row['hour']}. \n"

        for row in check_dict.get("site_inventory_exceeds", []):
            check_log += f"check_sites, site_inventory {row['id_location']}. "
            check_log += (
                f"Tank quantity superior to tank_capacity at hour {row['hour']}.\n"
            )

        for row in check_dict.get("site_doesntexist", []):
            check_log += f"check_sites."
            check_log += f"SiteInventory {row['id_location']} does not correspond to a location.\n"

        # Resources
        for row in check_dict.get("res_dr_01_intershift", []):
            check_log += f"aux_check_resources_dr_01, shift {row['id_shift']}. "
            check_log += f"Driver {row['id_driver']} does not respect minInterSHIFTDURATION before this shift.\n"

        for row in check_dict.get("res_dr_03_max_duration", []):
            check_log += f"aux_check_resources_dr_03, shift {row['id_shift']}. "
            check_log += (
                f"Driver {row['id_driver']} does not respect maxDrivingDuration.\n"
            )

        for row in check_dict.get("res_dr_08_driver_TW", []):
            check_log += f"check_resources_dr_08, shift {row['id_shift']}. "
            check_log += f"Shift is out of the time windows of the driver.\n"

        for row in check_dict.get("res_tl_01_shift_overlaps", []):
            check_log += f"aux_check_resources_tl_01, shift {row['id_shift']}. "
            check_log += (
                f"Trailer doesn't respect shift separation before this shift.\n"
            )

        for row in check_dict.get("res_tl_03_compatibility_dr_tr", []):
            check_log += f"aux_check_resources_tl_03, shift {row['id_shift']}. "
            check_log += (
                f"Trailer is not in the set of trailers compatible with the driver.\n"
            )

        # Quality of service
        for row in check_dict.get("qs_01_orders_satisfied", []):
            check_log += f"check_qs_01. "
            check_log += f"Missed order nª{row['num_order']} at customer {row['id_customer']}. \n"

        for row in check_dict.get("qs_02_runouts", []):
            check_log += f"check_qs_02."
            check_log += f"Customer {row['id_location']} ran out.\n"

        for row in check_dict.get("qs_03_callins", []):
            check_log += f"sub_check_qs_03, shift {row['id_shift']}. "
            check_log += f"Operation at location {row['id_location']} is out of the time windows of orders.\n"

        return check_log

    def is_base(self, location):
        return self.instance.is_base(location)

    def is_source(self, location):
        return self.instance.is_source(location)

    def is_customer(self, location):
        return self.instance.is_customer(location)

    def is_valid_location(self, location):
        return self.instance.is_valid_location(location)

    def is_customer_or_source(self, location):
        return self.instance.is_customer_or_source(location)

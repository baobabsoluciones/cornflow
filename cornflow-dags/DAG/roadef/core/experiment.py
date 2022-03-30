from .solution import Solution
from .instance import Instance
from cornflow_client import ExperimentCore
from pytups import SuperDict, TupList
from math import floor
import numpy as np


class Experiment(ExperimentCore):
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
            for s, (stop, next_stop) in enumerate(zip(shift['route'], shift['route'][1:])):
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
                duration=shift["route"][-1]["arrival"]
                         - shift["departure_time"],
                driving_duration = sum(
                    self.instance.get_time_between(
                        stop["location"],
                        next_stop["location"]
                    )
                    for stop, next_stop in zip(shift["route"], shift["route"][1:])
                )
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
    def check_solution(self):
        return SuperDict(
            {
                **self.check_shifts(),
                **self.check_sites(),
                **self.check_resources(),
                **self.check_service_quality(),
            }
        ).vfilter(lambda v: len(v))

    # ==================================
    # Verification of shifts constraints
    def check_shifts(self):
        check = SuperDict(
            c_02_timeline=SuperDict(),
            c_03_wrong_index=SuperDict(),
            c_03_setup_times=SuperDict(),
            c_04_customer_TW=SuperDict(),
            c_05_sites_accessible=SuperDict(),
            c_0607_inventory_trailer_negative=SuperDict(),
            c_0607_inventory_trailer_above_capacity=SuperDict(),
            c_0607_inventory_trailer_final_inventory=SuperDict(),
            c_0607_inventory_trailer_initial_inventory=SuperDict(),
            c_11_quantity_delivered=SuperDict(),
            c_16_customer_tank_exceeds=SuperDict(),
            c_16_customer_tank_too_low=SuperDict(),
            driver_and_trailer=SuperDict(),
        )

        for shift in self.solution.get_all_shifts():
            driver = shift.get("driver", None)
            trailer = shift.get("trailer", None)
            id_shift = shift.get("id_shift", None)
            if driver is None or trailer is None:
                check["driver_and_trailer"][id_shift] = 1
                continue
            check["c_02_timeline"].update(self.check_shift_02(shift, id_shift, driver))

            res_check_c03 = self.check_shift_03(shift, id_shift).vfilter(
                lambda v: len(v) != 0
            )
            check["c_03_wrong_index"].update(res_check_c03.get("wrong_index", []))
            check["c_03_setup_times"].update(res_check_c03.get("setup_time", []))
            check["c_04_customer_TW"].update(self.check_shift_04(shift, id_shift))
            check["c_05_sites_accessible"].update(
                self.check_shift_05(shift, id_shift, trailer)
            )
            check["c_11_quantity_delivered"].update(
                self.check_shift_11(shift, id_shift)
            )
            res_check_c16 = self.check_shift_16(shift, id_shift).vfilter(
                lambda v: len(v) != 0
            )
            check["c_16_customer_tank_exceeds"].update(res_check_c16.get("exceeds", []))
            check["c_16_customer_tank_too_low"].update(res_check_c16.get("too_low", []))

        checks_0607 = self.check_shift_0607().vfilter(lambda v: len(v) != 0)
        check["c_0607_inventory_trailer_negative"] = checks_0607.get(
            "inventory_negative", []
        )
        check["c_0607_inventory_trailer_above_capacity"] = checks_0607.get(
            "above_capacity", []
        )
        check["c_0607_inventory_trailer_final_inventory"] = checks_0607.get(
            "final_inventory", []
        )
        check["c_0607_inventory_trailer_initial_inventory"] = checks_0607.get(
            "initial_inventory", []
        )
        return check.vfilter(lambda v: len(v))

    # Checks that the timeline is coherent for each shift
    def check_shift_02(self, shift, id_shift, driver):
        """
        returns {(shift_id, location): 1, ... } for incoherent timeline at given location
        """
        check = SuperDict()
        last_point = self.instance.get_id_base()
        last_departure = shift["departure_time"]

        for operation in shift["route"]:
            current_point = operation["location"]
            travel_time = self.instance.get_time_between(last_point, current_point)
            layover_time = self.instance.get_driver_property(driver, "LayoverDuration")
            if (
                operation["arrival"]
                < last_departure
                + travel_time
                + operation["layover_before"] * layover_time
            ):
                check[(id_shift, current_point)] = 1
            last_point = current_point
            last_departure = operation["departure"]
        return check

    # Checks the loading and delivery times
    def check_shift_03(self, shift, id_shift):
        """
        returns {"wrong_index": {(id_shift, id_location): 1, ... } for non existent locations,
                 "setup_time":  {(id_shift, id_location): 1, ... } for operation that does not respect setup time }
        """
        check = SuperDict(wrong_index=SuperDict(), setup_time=SuperDict())
        id_operation = 1
        for operation in shift["route"][:-1]:
            if not self.is_valid_location(operation["location"]):
                check["wrong_index"][(id_shift, id_operation)] = 1
                continue
            location = operation["location"]
            if location > 0:
                setup_time = self.instance.get_location_property(
                    location, "setupTime"
                )
                if operation["departure"] < operation["arrival"] + setup_time:
                    check["setup_time"][(id_shift, location)] = 1
            id_operation += 1
        return check

    # Checks that the operations are performed during customers'time windows
    def check_shift_04(self, shift, id_shift):
        """
        returns {(shift_id, location): 1, ... } for operation out of customer's TW
        """
        check = SuperDict()
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
                check[(id_shift, location)] = 1
        return check

    # Checks that the loading and delivery sites are accessible for the vehicle
    def check_shift_05(self, shift, id_shift, trailer):
        """
        returns {(shift_id, location): 1, ... } for incompatible shift-location combination
        """
        check = SuperDict()
        for operation in shift["route"][:-1]:
            location = operation["location"]
            if self.is_customer_or_source(location):
                if trailer not in self.instance.get_location_property(
                    location, "allowedTrailers"
                ):
                    check[(id_shift, location)] = 1
        return check

    # Checks that the trailer's inventory is not negative and does not exceed capacity (06)
    # Checks that the initial quantity of a trailer on a shift is the end quantity of its previous shift (07)
    def check_shift_0607(self):
        """
        returns {"negative": {(id_shift, id_location): quantity, ... } for operation resulting in negative trailer inventory
                 "above_capacity": {(id_shift, id_location): quantity, ... } for operation resulting in excessive trailer inventory
                 "final_inventory": {id_shift: 1, ...} for shifts with inconsistent final inventory
                 "initial_inventory": {id_shift: 1, ...} for shifts with inconsistent initial inventory }
        """
        check = SuperDict(
            negative=SuperDict(),
            above_capacity=SuperDict(),
            final_inventory=SuperDict(),
            initial_inventory=SuperDict(),
        )
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
            # Constraints (06)
            last_quantity = shift["initial_quantity"]

            for operation in shift["route"]:
                quantity = last_quantity + operation["quantity"]
                location = operation["location"]
                if round(quantity, 2) < 0:
                    check["negative"][(id_shift, location)] = quantity
                elif round(quantity, 2) > self.instance.get_trailer_property(
                    trailer, "Capacity"
                ):
                    check["above_capacity"][(id_shift, location)] = quantity

                last_quantity = quantity
            # Constraints (07)
            if round(aux_info_shift[id_shift]["final_inventory"], 2) != round(
                last_quantity, 2
            ):
                check["final_inventory"][id_shift] = 1
            if round(last_trailer_quantity[trailer], 2) != round(
                shift["initial_quantity"], 2
            ):
                check["initial_inventory"][id_shift] = 1
            last_trailer_quantity[trailer] = last_quantity
        check = check.vfilter(lambda v: len(v) != 0)
        return check

    # Checks that the quantity delivered at a customer is positive and the quantity loaded at a source is also positive
    def check_shift_11(self, shift, id_shift):
        """
        returns {(shift_id, location): quantity, ... } for operation with wrong sign
        """
        check = SuperDict()
        for i in range(1, len(shift["route"]) + 1):
            operation = shift["route"][i - 1]
            location = operation["location"]
            if self.is_source(location) and operation["quantity"] < 0:
                check[(id_shift, location)] = operation["quantity"]
            elif self.is_customer(location) and operation["quantity"] > 0:
                check[(id_shift, location)] = operation["quantity"]
        return check

    # For each delivery, the delivery must be smaller than the customer's tank's capacity
    def check_shift_16(self, shift, id_shift):
        """
        returns {"exceeds": {(id_shift, id_location): quantity, ... } for
                        operation with quantity above trailer's capacity
                 "too_low": {(id_shift, id_location): quantity, ... } for
                        operation with quantity < min_quantity
                }
        """
        check = SuperDict(exceeds=SuperDict(), too_low=SuperDict())
        for i in range(1, len(shift["route"]) + 1):
            operation = shift["route"][i - 1]
            location = operation["location"]

            if not self.is_customer(location):
                continue

            call_in = self.instance.get_customer_property(location, "callIn")
            if call_in == 0:
                capacity = self.instance.get_customer_property(location, "Capacity")
                min_ope_quantity = self.instance.get_customer(location).get(
                    "MinOperationQuantity", 0
                )
                if -operation["quantity"] > capacity:
                    check["exceeds"][(id_shift, location)] = operation["quantity"]
                elif -operation["quantity"] < min_ope_quantity:
                    check["too_low"][(id_shift, location)] = operation["quantity"]
        check = check.vfilter(lambda v: len(v) != 0)
        return check

    # =================================
    # Verification of sites constraints
    def check_sites(self):
        """
        returns {"site_inventory_negative": {(location, time): inventory, ... } for inventories > tank_capacity
                 "site_inventory_exceeds": {(location, time): inventory, ... } for  negative inventories
                 "site_doesntexist": {location: 1}   for nonexistent locations
                }
        """
        check = SuperDict(
            site_inventory_negative=SuperDict(),
            site_inventory_exceeds=SuperDict(),
            site_doesntexist=SuperDict(),
        )
        operation_quantities = []

        for location in range(1 + self.nb_sources + self.nb_customers):
            operation_quantities.append([0] * self.horizon)

        site_inventories = self.calculate_inventories()
        for site_inventory in site_inventories.values():
            location = site_inventory["location"]
            if not self.is_valid_location(location):
                check["site_doesntexist"][location] = 1
                continue
            if location <= 1 + self.nb_sources:
                continue
            call_in = self.instance.get_customer_property(location, "callIn")
            if call_in == 1:
                continue
            for i in range(self.horizon):
                if round(site_inventory["tank_quantity"][i], 3) < 0:
                    check["site_inventory_negative"][location, i] = site_inventory[
                        "tank_quantity"
                    ][i]
                if round(
                    site_inventory["tank_quantity"][i], 3
                ) > self.instance.get_customer_property(location, "Capacity"):
                    check["site_inventory_exceeds"][location, i] = site_inventory[
                        "tank_quantity"
                    ][i]
        check = check.vfilter(lambda v: len(v) != 0)
        return check

    # =====================================
    # Verification of resources constraints
    def check_resources(self):
        check = SuperDict(
            res_dr_01_intershift=SuperDict(),
            res_dr_03_max_duration=SuperDict(),
            res_dr_08_driver_TW=SuperDict(),
            res_tl_01_shift_overlaps=SuperDict(),
            res_tl_03_compatibility_dr_tr=SuperDict(),
        )
        end_of_last_shifts_drivers = [0] * self.nb_drivers
        end_of_last_shifts_trailer = [0] * self.nb_trailers
        aux_info_shift = self.get_aux_info_shift()

        for shift in sorted(
            list(self.solution.get_all_shifts()), key=lambda x: x["departure_time"]
        ):
            driver = shift.get("driver", None)
            trailer = shift.get("trailer", None)
            id_shift = shift.get("id_shift", None)
            if driver is None or trailer is None:
                continue
            # DRIVERS
            if self.check_resources_dr_01(
                shift, driver, end_of_last_shifts_drivers[driver]
            ):
                check["res_dr_01_intershift"][id_shift, driver] = 1

            check_03 = self.check_resources_dr_03(shift, driver)
            if check_03 is not None:
                check["res_dr_03_max_duration"][id_shift, driver] = check_03

            if self.check_resources_dr_08(shift, id_shift, driver):
                check["res_dr_08_driver_TW"][id_shift] = 1

            # TRAILERS
            if self.check_resources_tl_01(shift, end_of_last_shifts_trailer[trailer]):
                check["res_tl_01_shift_overlaps"][id_shift] = 1

            if self.check_resources_tl_03(driver, trailer):
                check["res_tl_03_compatibility_dr_tr"][id_shift] = 1

            #
            end_of_last_shifts_trailer[trailer] = aux_info_shift[id_shift][
                "arrival_time"
            ]
            end_of_last_shifts_drivers[driver] = aux_info_shift[id_shift][
                "arrival_time"
            ]
        return check.vfilter(lambda v: len(v))

    # Checks that the minimum delay between two shifts is respected
    def check_resources_dr_01(self, shift, driver, end_of_last_shift):
        """
        returns True for shifts not respecting minInterShiftDuration
        """
        min_delay = self.instance.get_driver_property(driver, "minInterSHIFTDURATION")
        return (
            end_of_last_shift != 0
            and shift["departure_time"] < end_of_last_shift + min_delay
        )

    # Checks that the shift respects maximum duration
    def check_resources_dr_03(self, shift, driver):
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
        return check

    # Checks that the shift fits into the driver's time windows
    def check_resources_dr_08(self, shift, id_shift, driver):
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
    def check_resources_tl_01(self, shift, end_of_last_shift):
        """
        returns True for shifts using the same trailer as other currently running shift
        """
        return end_of_last_shift != 0 and shift["departure_time"] < end_of_last_shift

    # Checks that the driver and the trailer and compatible
    def check_resources_tl_03(self, driver, trailer):
        """
        returns True for incompatible driver-trailer combinations
        """
        return trailer not in self.instance.get_driver_property(driver, "trailer")

    # ===========================================
    # Verification of service quality constraints
    def check_service_quality(self):
        return SuperDict(
            qs_01_orders_satisfied=self.check_qs_01(),
            qs_02_runouts=self.check_qs_02(),
            qs_03_callins=self.check_qs_03(),
        ).vfilter(lambda v: len(v))

    # Checks that all orders having a time window ending before the planning horizon are satisfied
    def check_qs_01(self):
        """
        returns {(customer, num_order): 1, ... } for not delivered orders
        """
        check = SuperDict()
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
                    check[c + offset_customer, o] = 1

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
    def check_qs_02(self):
        """
        returns {location: nb_run_outs, ... } for locations experiencing runouts
        """
        check = SuperDict()
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
                check[site] = nb_inventory_run_out
        return check

    # Checks that callIn customers only receive deliveries linked to an order
    def check_qs_03(self):
        check = SuperDict()
        for shift in self.solution.get_all_shifts():
            id_shift = shift["id_shift"]
            check.update(self.sub_check_qs_03(shift, id_shift))
        return check

    # Checks that the shift's operations on callIn customers are related to an order
    def sub_check_qs_03(self, shift, id_shift):
        """
        returns {(shift_id, location): 1, ... } for deliveries not related to an order to callIn customer
        """
        check = SuperDict()

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
                check[(id_shift, location)] = 1
        return check

    def generate_log(self, check_dict):
        """
        Transforms the dictionary returned by check_solution into a string log
        """
        check_log = ""

        # Shifts
        for id_shift in check_dict.get("driver_and_trailer", dict()):
            check_log += f"Shift : {id_shift} has no driver or no trailer.\n"
        for id_shift, current_point in check_dict.get("c_02_timeline", dict()):
            check_log += f"check_shift_02, shift {id_shift}. "
            check_log += f"Operation at location {current_point} arrives too early.\n"
        for id_shift, id_operation in check_dict.get("c_03_wrong_index", dict()):
            check_log += f"check_shift_03, shift {id_shift}. "
            check_log += f"Operation nº{id_operation} has a wrong location index.\n"
        for id_shift, location in check_dict.get("c_03_setup_times", dict()):
            check_log += f"check_shift_03, shift {id_shift}. "
            check_log += (
                f"Departure of operation at location {location} is too early.\n"
            )
        for id_shift, location in check_dict.get("c_04_customer_TW", dict()):
            check_log += f"check_shift_04, shift {id_shift}. "
            check_log += (
                f"Operation at location {location} is out of the time windows.\n"
            )
        for id_shift, location in check_dict.get("c_05_sites_accessible", dict()):
            check_log += f"check_shift_05, shift {id_shift}. "
            check_log += (
                f"Operation at location {location} can't accept this trailer.\n"
            )
        for id_shift, id_location in check_dict.get(
            "c_0607_inventory_trailer_negative", dict()
        ):
            check_log += f"check_shift_06, shift {id_shift}. "
            check_log += f"Operation at location {location} makes the trailer's inventory negative.\n"
        for id_shift, id_location in check_dict.get(
            "c_0607_inventory_trailer_above_capacity", dict()
        ):
            check_log += f"check_shift_06, shift {id_shift}. "
            check_log += f"Operation at location {location} makes the trailer's inventory above its capacity.\n"
        for id_shift in check_dict.get(
            "c_0607_inventory_trailer_final_inventory", dict()
        ):
            check_log += f"check_shift_07, shift {id_shift}. "
            check_log += (
                f"The trailer's operations do not correspond to its final inventory.\n"
            )
        for id_shift in check_dict.get(
            "c_0607_inventory_trailer_initial_inventory", dict()
        ):
            check_log += f"check_shift_07, shift {id_shift}. "
            check_log += (
                f"The initial inventory is not coherent with last shift of the trailer.\n"
            )
        for shift_id, location in check_dict.get("c_11_quantity_delivered", dict()):
            check_log += f"check_shift_11, shift {id_shift}. "
            check_log += f"Operation at location {location} has wrong sign.\n"
        for id_shift, location in check_dict.get("c_16_customer_tank_exceeds", dict()):
            check_log += f"check_shift_16, shift {id_shift}. "
            check_log += f"Operation at customer {location} has quantity higher than tank's capacity.\n"
        for id_shift, location in check_dict.get("c_16_customer_tank_too_low", dict()):
            check_log += f"check_shift_16, shift {id_shift}. "
            check_log += f"Operation at customer {location} has quantity lower than minimum quantity.\n"

        # Sites
        for location, i in check_dict.get("site_inventory_negative", dict()):
            check_log += f"check_sites, site_inventory {location}. "
            check_log += f"Tank quantity strictly negative  at step {i}. \n"
        for location, i in check_dict.get("site_inventory_exceeds", dict()):
            check_log += f"check_sites, site_inventory {location}. "
            check_log += f"Tank quantity superior to tank_capacity at step {i}.\n"
        for location in check_dict.get("site_doesntexist", dict()):
            check_log += f"check_sites."
            check_log += (
                f"SiteInventory {location} does not correspond to a location.\n"
            )

        # Resources
        for id_shift, driver in check_dict.get("res_dr_01_intershift", dict()):
            check_log += f"check_resources_dr_01, shift {id_shift}. "
            check_log += f"Driver {driver} does not respect minInterSHIFTDURATION before this shift.\n"
        for id_shift, driver in check_dict.get("res_dr_03_max_duration", dict()):
            check_log += f"check_resources_dr_03, shift {id_shift}. "
            check_log += f"Driver {driver} does not respect maxDrivingDuration.\n"
        for id_shift in check_dict.get("res_dr_08_driver_TW", dict()):
            check_log += f"check_resources_dr_08, shift {id_shift}. "
            check_log += f"Shift is out of the time windows of the driver.\n"
        for id_shift in check_dict.get("res_tl_01_shift_overlaps", dict()):
            check_log += f"check_resources_tl_01, shift {id_shift}. "
            check_log += (
                f"Trailer doesn't respect shift separation before this shift.\n"
            )
        for id_shift in check_dict.get("res_tl_03_compatibility_dr_tr", dict()):
            check_log += f"check_resources_tl_03, shift {id_shift}. "
            check_log += (
                f"Trailer is not in the set of trailers compatible with the driver.\n"
            )

        # Quality of service
        for customer, order in check_dict.get("qs_01_orders_satisfied", dict()):
            check_log += f"check_qs_01. "
            check_log += f"Missed order nª{order} at customer {customer}. \n"
        for site in check_dict.get("qs_02_runouts", dict()):
            check_log += f"check_qs_02."
            check_log += f"Customer {site} ran out.\n"
        for id_shift, location in check_dict.get("qs_03_callins", dict()):
            check_log += f"sub_check_qs_03, shift {id_shift}. "
            check_log += f"Operation at location {location} is out of the time windows of orders.\n"

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

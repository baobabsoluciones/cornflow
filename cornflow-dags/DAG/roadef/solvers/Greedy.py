from ..core import Experiment, Solution
from random import randint
from math import floor, inf


class Greedy(Experiment):
    def __init__(self, instance, solution=None):
        super().__init__(instance, solution)
        self.last_refill_customers = dict()
        self.trailer_of_driver = dict()
        self.driver_of_trailer = dict()
        self.cumulated_driving_duration = dict()
        self.last_location = (
            dict()  # The property "time" contains the departure time of the last location
        )  # i.e. the arrival time + the setup time
        self.inventory_trailers = dict()
        self.current_shift = dict()
        self.first_idx_customer = 1 + len(self.instance.get_id_sources())
        self.nb_drivers = self.instance.get_number_drivers()
        self.nb_working_drivers = self.nb_drivers
        self.working_drivers = list(self.instance.get_id_drivers())
        self.stock_outs = []
        self.delayed = []
        self.idx_shift = 1
        self.interval_between_refills = 60 * 12
        self.max_slack = inf
        self.log = ""
        self.select_at_random = False
        self.solver = "Greedy"
        self.solution_data = dict()
        self.site_inventories = self.calculate_inventories()

    def solve(self, config):
        self.initialize()
        if config:
            self.max_slack = config.get("maxSlack", inf)

        customers_to_visit = [
            dict(index=idx_c, last_possible_visit=self.last_possible_visit(idx_c))
            for idx_c in self.instance.get_id_customers()
            if not self.instance.is_call_in_customer(idx_c)
            and self.last_possible_visit(idx_c) is not None
        ]
        last_possible_visits = {
            item["index"]: item["last_possible_visit"] for item in customers_to_visit
        }

        customers_to_visit = sorted(
            customers_to_visit, key=lambda x: x["last_possible_visit"]
        )
        slack_times_and_distances = self.compute_slack_and_distances(
            last_possible_visits
        )

        while not customers_to_visit == []:
            if self.select_at_random:
                selected = randint(0, len(customers_to_visit) - 1)
            else:
                selected = 0
            customer_object = customers_to_visit[selected]
            customer = customers_to_visit[selected]["index"]

            # Select the driver closest to the customer among the drivers that have a positive slack
            #   (i.e. the ones that can arrive before the customer runs out)
            driver, delay, last_choice = self.positive_argmin(
                slack_times_and_distances, customer
            )

            if driver is None and not delay:  # No possible routes for this customer
                self.stock_outs.append(customer)
                customers_to_visit.remove(customer_object)
            elif (
                driver is None and delay
            ):  # Possible routes may exist but none at the moment
                customers_to_visit.remove(customer_object)
                self.delayed.append(customer_object)
            else:
                trailer = self.trailer_of_driver[driver]
                max_delivery = self.inventory_trailers[trailer]

                travel_time = self.instance.get_time_between(
                    self.last_location[trailer]["location"], customer
                )
                instant = self.last_location[trailer]["time"] + travel_time

                if instant + self.max_slack < last_possible_visits[customer]:
                    customers_to_visit += self.delayed
                    customers_to_visit = sorted(
                        customers_to_visit, key=lambda x: x["last_possible_visit"]
                    )
                    self.all_trailers_back_to_base()
                    self.pause(12 * 60)
                    slack_times_and_distances = self.compute_slack_and_distances(
                        last_possible_visits
                    )
                    self.delayed = []
                    continue

                if (  # The customer can never be delivered
                    last_choice and floor(instant / self.unit) >= self.horizon + 1
                ):
                    self.stock_outs.append(customer)
                    customers_to_visit.remove(customer_object)

                else:
                    demand_1day = self.demand_1d(customer, instant)

                    if self.site_inventories[customer]["tank_quantity"][
                        floor(instant / 60)
                    ] < self.instance.get_customer_property(
                        customer, "Capacity"
                    ) - self.instance.get_customer_property(
                        customer, "MinOperationQuantity"
                    ):
                        res = 1
                        if max_delivery < min(
                            demand_1day,
                            self.instance.get_trailer_property(trailer, "Capacity"),
                        ):  # The quantity delivered won't be enough to cover the customer's consumption for a day
                            res, source = self.find_closest_source(
                                trailer, driver, customer
                            )
                            if res in [0, 1]:  # The source can be added to the route
                                self.insert_source_to_route(source, trailer, driver)
                                slack_times_and_distances = (
                                    self.compute_slack_and_distances(
                                        last_possible_visits
                                    )
                                )
                                self.back_to_base(slack_times_and_distances)

                        if res == 1 and (
                            slack_times_and_distances[driver][
                                customer - self.first_idx_customer
                            ][0]
                            >= 0
                            or last_choice
                        ):  # The customer can be added to the route
                            travel_time = self.instance.get_time_between(
                                self.last_location[trailer]["location"], customer
                            )
                            arrival = self.last_location[trailer]["time"] + travel_time
                            if (
                                last_choice
                                and floor(arrival / self.unit) >= self.horizon + 1
                            ):  # The trailer will arrive after the horizon
                                self.stock_outs.append(customer)
                                customers_to_visit.remove(customer_object)
                            else:
                                self.insert_customer_to_route(customer, trailer, driver)

                                customers_to_visit.remove(customer_object)
                                last_visit_possible = self.last_possible_visit(customer)

                                if (
                                    last_visit_possible is not None
                                ):  # The customer will need another delivery
                                    customers_to_visit.append(
                                        dict(
                                            index=customer,
                                            last_possible_visit=last_visit_possible,
                                        )
                                    )
                                    last_possible_visits[customer] = last_visit_possible

                                customers_to_visit = sorted(
                                    customers_to_visit + self.delayed,
                                    key=lambda x: x["last_possible_visit"],
                                )
                                self.delayed = []

                                slack_times_and_distances = (
                                    self.compute_slack_and_distances(
                                        last_possible_visits
                                    )
                                )
                                self.back_to_base(slack_times_and_distances)
                                slack_times_and_distances = (
                                    self.compute_slack_and_distances(
                                        last_possible_visits
                                    )
                                )
                        elif res == 0:  # A source was added but not the customer
                            customers_to_visit = sorted(
                                customers_to_visit + self.delayed,
                                key=lambda x: x["last_possible_visit"],
                            )
                            self.delayed = []

                            slack_times_and_distances = (
                                self.compute_slack_and_distances(last_possible_visits)
                            )
                            self.back_to_base(slack_times_and_distances)
                        # The source and customer could not be added.
                        # The customer can not be served by this trailer
                        elif res == -1:
                            slack_times_and_distances[driver][
                                customer - self.first_idx_customer
                            ][0] = 0
                    else:
                        customers_to_visit.remove(customer_object)
                        self.delayed.append(customer_object)
            if not customers_to_visit:  # All customers have been delivered OR delayed
                customers_to_visit = self.delayed.copy()
                customers_to_visit = sorted(
                    customers_to_visit, key=lambda x: x["last_possible_visit"]
                )
                self.all_trailers_back_to_base()
                self.pause(12 * 60)
                slack_times_and_distances = self.compute_slack_and_distances(
                    last_possible_visits
                )
                self.delayed = []
        self.all_trailers_back_to_base()
        self.solution = Solution(self.solution_data)
        return 1

    def initialize(self):
        self.last_refill_customers = {
            key: -self.interval_between_refills
            for key in self.instance.get_id_customers()
        }
        self.cumulated_driving_duration = {
            key: 0 for key in self.instance.get_id_drivers()
        }

        self.last_location = {
            key: dict(location=self.instance.get_id_base(), time=0)
            for key in self.instance.get_id_trailers()
        }

        self.assign_drivers_and_trailers()

        self.inventory_trailers = {
            key: self.instance.get_trailer_property(key, "InitialQuantity")
            for key in self.instance.get_id_trailers()
        }

        self.current_shift = {
            key: dict(day=None) for key in self.instance.get_id_trailers()
        }
        for key in self.instance.get_id_trailers():
            self.current_shift[key]["id_shift"] = self.idx_shift
            self.idx_shift += 1

    def assign_drivers_and_trailers(self):
        """
        Assigns each driver to a trailer
        """
        acceptable = False
        already_assigned_trailers = []
        assignment = dict()
        nb_drivers = self.instance.get_number_drivers()
        nb_trailers = self.instance.get_number_trailers()
        while not acceptable:
            for id_driver in self.instance.get_id_drivers():
                driver = self.instance.get_driver(id_driver)
                available_trailers = list(
                    set(driver["trailer"]) - set(already_assigned_trailers)
                )
                if len(available_trailers) != 0:
                    id_trailer = available_trailers[
                        randint(0, len(available_trailers)) - 1
                    ]
                    already_assigned_trailers.append(id_trailer)
                    assignment[id_driver] = id_trailer

            if len(assignment) == min(nb_drivers, nb_trailers):
                acceptable = True
            else:
                assignment = dict()
                already_assigned_trailers = []
        self.trailer_of_driver = assignment
        self.nb_working_drivers = len(self.trailer_of_driver)
        self.driver_of_trailer = {
            self.trailer_of_driver[driver]: driver
            for driver in self.trailer_of_driver.keys()
        }
        self.working_drivers = list(assignment.keys())

    def last_possible_visit(self, customer):
        """
        Computes the last possible hour to visit the customer in order to avoid a stock out
        """
        if self.last_refill_customers[customer] < 0:
            hour_last_refill = 0
        else:
            hour_last_refill = floor(self.last_refill_customers[customer] / 60)

        instant = hour_last_refill
        while (
            instant < self.horizon - 1
            and self.site_inventories[customer]["tank_quantity"][instant] > 0
        ):
            instant += 1
        if self.site_inventories[customer]["tank_quantity"][instant] <= 0:
            return max(0, 60 * (instant - 1))
        return None

    def back_to_base(self, slack_times_and_distances):
        """
        All trailers that can not deliver any more customers go back to the base and end their shifts
        """
        going_back_to_base = []

        for driver in self.working_drivers:
            trailer = self.trailer_of_driver[driver]
            bool_back_to_base = True

            for customer in range(len(slack_times_and_distances[driver])):
                if slack_times_and_distances[driver][customer][0] > 0:
                    bool_back_to_base = False
            if bool_back_to_base:
                going_back_to_base.append((trailer, driver))

        for trailer, driver in going_back_to_base:
            if self.inventory_trailers[trailer] != self.instance.get_trailer_property(
                trailer, "Capacity"
            ):
                res, source = self.find_closest_source(
                    trailer, driver, None
                )  # 1 if the route does not exceed max duration
                if res == 1:
                    self.insert_source_to_route(source, trailer, driver)
            self.insert_base_to_route(trailer, driver)
            self.current_shift[trailer]["id_shift"] = self.idx_shift
            self.current_shift[trailer]["day"] = None
            self.idx_shift += 1

    def all_trailers_back_to_base(self):
        """
        All trailers go back to the base and end their shifts
        """
        base = self.instance.get_id_base()

        for driver in self.working_drivers:
            trailer = self.trailer_of_driver[driver]
            if self.last_location[trailer]["location"] != base:
                # Try going by a source
                if self.inventory_trailers[
                    trailer
                ] != self.instance.get_trailer_property(trailer, "Capacity"):
                    res, source = self.find_closest_source(
                        trailer, driver, None
                    )  # 1 if the route does not exceed max duration
                    if res == 1:
                        self.insert_source_to_route(source, trailer, driver)

                # Go back to base
                self.insert_base_to_route(trailer, driver)
                self.current_shift[trailer]["day"] = None
                self.current_shift[trailer]["id_shift"] = self.idx_shift
                self.idx_shift += 1

    def pause(self, duration):
        for driver in self.working_drivers:
            trailer = self.trailer_of_driver[driver]
            if self.last_location[trailer]["location"] == self.instance.get_id_base():
                self.last_location[trailer]["time"] += duration

    def positive_argmin(self, slack_times_and_distances, customer):
        """
        Finds the driver/trailer pair that is closest to the customer among those that have a positive slack
        (i.e. the ones that can arrive to the customer before it runs out)
        :return: Finds the driver/trailer pair that is closest to the customer among those that have a positive slack
        (i.e. the ones that can arrive to the customer before it runs out)
        """
        slacks_customer = {
            driver: slack_times_and_distances[driver][
                customer - self.first_idx_customer
            ][0]
            for driver in self.working_drivers
        }
        dist_to_cust = {
            driver: slack_times_and_distances[driver][
                customer - self.first_idx_customer
            ][1]
            for driver in self.working_drivers
        }
        if len(slacks_customer) == 0:
            return None, False, False
        mini = None
        argmin = None
        delay_customer = False

        for driver in set(slacks_customer.keys()).intersection(
            set(
                [
                    self.driver_of_trailer[trailer]
                    for trailer in self.instance.get_customer_property(
                        customer, "allowedTrailers"
                    )
                ]
            )
        ):
            if mini is None and slacks_customer[driver] > 0:
                mini = dist_to_cust[driver]
                argmin = driver
            elif mini is not None:
                if 0 < slacks_customer[driver] and dist_to_cust[driver] < mini:
                    mini = dist_to_cust[driver]
                    argmin = driver
            if slacks_customer[driver] == 0:
                delay_customer = True
        if (
            argmin is None and not delay_customer
        ):  # matrix[i, customer - self.first_idx_customer, 0] < 0 for all i
            closest_to_zero = None
            arg = None

            for driver in slacks_customer.keys():
                if closest_to_zero is None:
                    closest_to_zero = dist_to_cust[driver]
                    arg = driver
                else:
                    if slacks_customer[driver] > closest_to_zero:
                        closest_to_zero = slacks_customer[driver]
                        arg = driver
                    elif slacks_customer[driver] == closest_to_zero:
                        if dist_to_cust[driver] < dist_to_cust[arg]:
                            closest_to_zero = dist_to_cust[driver]
                            arg = driver
            return arg, False, True
        else:
            return argmin, delay_customer, False

    def compute_slack_and_distances(self, last_possible_visits):
        """
        Computes for each (driver, customer) pair the slack (i.e. the difference between the time of the last possible
        visit to avoid a run out and the arrival time of the driver) and the current distance between the
        customer and the driver
        """
        slack_times_and_distances = {driver: [] for driver in self.working_drivers}
        for driver in slack_times_and_distances.keys():
            for customer in range(self.nb_customers):
                slack_times_and_distances[driver].append([0, 0])

        for driver in self.working_drivers:
            trailer = self.trailer_of_driver[driver]
            max_duration = self.instance.get_driver_property(
                driver, "maxDrivingDuration"
            )

            for customer in last_possible_visits.keys():
                if self.last_location[trailer]["location"] != customer:
                    travel_time = self.instance.get_time_between(
                        self.last_location[trailer]["location"], customer
                    )
                    back_to_base_time = self.instance.get_time_between(
                        customer, self.instance.get_id_base()
                    )

                    slack_time = last_possible_visits[customer] - (
                        self.last_location[trailer]["time"] + travel_time
                    )
                    dist = self.instance.get_distance_between(
                        self.last_location[trailer]["location"], customer
                    )

                    arrival_time = self.last_location[trailer]["time"] + travel_time
                    # Checking that adding this location to the route would not make it exceed maximum duration
                    if (
                        travel_time
                        + self.cumulated_driving_duration[driver]
                        + back_to_base_time
                        <= max_duration
                        and arrival_time
                        >= self.last_refill_customers[customer]
                        + self.interval_between_refills
                    ):
                        slack_times_and_distances[driver][
                            customer - self.first_idx_customer
                        ][0] = slack_time
                        slack_times_and_distances[driver][
                            customer - self.first_idx_customer
                        ][1] = dist
                    else:
                        slack_times_and_distances[driver][
                            customer - self.first_idx_customer
                        ][0] = 0
                        slack_times_and_distances[driver][
                            customer - self.first_idx_customer
                        ][1] = -1
        return slack_times_and_distances

    def demand_1d(self, customer, instant):
        """
        Computes the quantity to deliver to the customer if we want them to not have a stock-out in the next 24 hours
        """

        remaining_instant_t = self.site_inventories[customer]["tank_quantity"][
            floor(instant / 60)
        ]

        consumption_1d = sum(
            self.instance.get_customer_property(customer, "Forecast")[
                instant // 60 : instant // 60 + 24
            ]
        )

        mean_consumption = (
            sum(self.instance.get_customer_property(customer, "Forecast"))
            / self.horizon
        )

        return max(0, consumption_1d - remaining_instant_t, mean_consumption)

    # Computes the maximum quantity that can be delivered to the customer
    def max_demand(self, customer, instant):
        hour_arrival = floor(instant / 60)
        inventory_when_arrival = self.site_inventories[customer]["tank_quantity"][
            hour_arrival
        ]

        return (
            self.instance.get_customer_property(customer, "Capacity")
            - inventory_when_arrival
        )

    def find_closest_source(self, trailer, driver, customer):
        """
        * If customer is not None, computes the closest source between the current_position of the trailer and the customer
        Taking into account the fact that the driver should have the time to go back to the base without exceeding the
        maxDrivingDuration
        :return: an integer that is 1 if the source and the customer can be added to the shift without exceeding
        maxDrivingDuration, 0 if only the source can be added and -1 if none: and
        the id of the source if one was found
        * If customer is None, computes the closest source to the current position of the trailer.
        :return: an integer that is 1 if the source can be added, -1 if not; and the id of the source if one was found
        """
        if customer is not None:
            mini = None
            min_source = None
            part_mini = None

            for source in self.instance.get_id_sources():
                trailer_position = self.last_location[trailer]["location"]
                partial_time = self.instance.get_time_between(trailer_position, source)
                total_time = partial_time + self.instance.get_time_between(
                    source, customer
                )
                if mini is None:
                    mini = total_time
                    min_source = source
                    part_mini = partial_time
                elif total_time < mini:
                    mini = total_time
                    min_source = source
                    part_mini = partial_time

            travel_back_from_source = self.instance.get_time_between(
                min_source, self.instance.get_id_base()
            )
            travel_back_from_customer = self.instance.get_time_between(
                customer, self.instance.get_id_base()
            )

            if mini + self.cumulated_driving_duration[
                driver
            ] + travel_back_from_customer <= self.instance.get_driver_property(
                driver, "maxDrivingDuration"
            ):
                return 1, min_source
            elif part_mini + self.cumulated_driving_duration[
                driver
            ] + travel_back_from_source <= self.instance.get_driver_property(
                driver, "maxDrivingDuration"
            ):
                return 0, min_source
            else:
                return -1, None
        else:
            min_source = None
            part_mini = None

            for source in self.instance.get_id_sources():
                trailer_position = self.last_location[trailer]["location"]
                partial_time = self.instance.get_time_between(trailer_position, source)
                if part_mini is None:
                    min_source = source
                    part_mini = partial_time
                elif partial_time < part_mini:
                    min_source = source
                    part_mini = partial_time
            travel_back_from_source = self.instance.get_time_between(
                min_source, self.instance.get_id_base()
            )
            if part_mini + self.cumulated_driving_duration[
                driver
            ] + travel_back_from_source <= self.instance.get_driver_property(
                driver, "maxDrivingDuration"
            ):
                return 1, min_source
            else:
                return -1, None

    def insert_customer_to_route(self, customer, trailer, driver):
        travel_time = self.instance.get_time_between(
            self.last_location[trailer]["location"], customer
        )
        day = self.current_shift[trailer]["day"]
        if day is None:
            day = self.last_location[trailer]["time"] // (60 * 24)
            self.current_shift[trailer]["day"] = day

        id_shift = self.current_shift[trailer]["id_shift"]

        if self.solution_data.get(id_shift) is None:  # First step of the shift
            new_shift = dict(
                driver=driver,
                trailer=trailer,
                departure_time=self.last_location[trailer]["time"],
                initial_quantity=self.inventory_trailers[trailer],
                route=[],
                arrival_time=None,
                id_shift=id_shift,
            )

            new_shift["route"].append(
                dict(
                    location=self.instance.get_id_base(),
                    quantity=0,  # Quantity loaded or delivered at the base
                    arrival=self.last_location[trailer]["time"],
                    departure=self.last_location[trailer]["time"],
                    layover_before=0,
                    driving_time_before_layover=0,
                    cumulated_driving_time=0,
                )
            )
            self.solution_data[id_shift] = new_shift

        arrival = travel_time + self.last_location[trailer]["time"]
        # quantity = self.determine_quantity(trailer, customer, arrival)
        quantity = self.determine_max_quantity(trailer, customer, arrival)
        setup_time = self.instance.get_customer_property(customer, "setupTime")

        new_step = dict(
            location=customer,
            quantity=-quantity,
            arrival=arrival,
            departure=arrival + setup_time,
            layover_before=0,
            driving_time_before_layover=0,
            cumulated_driving_time=self.cumulated_driving_duration[driver]
            + travel_time,
        )
        self.solution_data[id_shift]["route"].append(new_step)

        self.last_refill_customers[customer] = arrival
        self.cumulated_driving_duration[driver] += travel_time
        self.last_location[trailer]["time"] += travel_time + setup_time
        self.last_location[trailer]["location"] = customer
        self.inventory_trailers[trailer] -= quantity

        next_hour = floor(arrival / self.unit)
        for t in range(next_hour, self.horizon):
            self.site_inventories[customer]["tank_quantity"][t] += quantity

    def insert_source_to_route(self, source, trailer, driver):
        travel_time = self.instance.get_time_between(
            self.last_location[trailer]["location"], source
        )
        day = self.current_shift[trailer]["day"]
        if day is None:
            day = self.last_location[trailer]["time"] // (60 * 24)
        self.current_shift[trailer]["day"] = day
        id_shift = self.current_shift[trailer]["id_shift"]

        if self.solution_data.get(id_shift) is None:  # First step of the shift
            new_shift = dict(
                driver=driver,
                trailer=trailer,
                departure_time=self.last_location[trailer]["time"],
                initial_quantity=self.inventory_trailers[trailer],
                route=[],
                arrival_time=None,
                id_shift=id_shift,
            )

            new_shift["route"].append(
                dict(
                    location=self.instance.get_id_base(),
                    quantity=0,  # Quantity loaded or delivered at the base
                    arrival=self.last_location[trailer]["time"],
                    departure=self.last_location[trailer]["time"],
                    layover_before=0,
                    driving_time_before_layover=0,
                    cumulated_driving_time=0,
                )
            )
            self.solution_data[id_shift] = new_shift

        arrival = travel_time + self.last_location[trailer]["time"]
        quantity = (
            self.instance.get_trailer_property(trailer, "Capacity")
            - self.inventory_trailers[trailer]
        )
        setup_time = self.instance.get_location_property(source, "setupTime")

        new_step = dict(
            location=source,
            quantity=+quantity,
            arrival=arrival,
            departure=arrival + setup_time,
            layover_before=0,
            driving_time_before_layover=0,
            cumulated_driving_time=self.cumulated_driving_duration[driver]
            + travel_time,
        )
        self.solution_data[id_shift]["route"].append(new_step)

        self.cumulated_driving_duration[driver] += travel_time
        self.last_location[trailer]["time"] += travel_time + setup_time
        self.last_location[trailer]["location"] = source
        self.inventory_trailers[trailer] += quantity

    def insert_base_to_route(self, trailer, driver):
        base = self.instance.get_id_base()
        travel_time = self.instance.get_time_between(
            self.last_location[trailer]["location"], base
        )
        day = self.current_shift[trailer]["day"]
        if day is None:
            day = self.last_location[trailer]["time"] // (60 * 24)
            self.current_shift[trailer]["day"] = day
        id_shift = self.current_shift[trailer]["id_shift"]

        if self.solution_data.get(id_shift) is None:  # First step of the shift
            return

        arrival = travel_time + self.last_location[trailer]["time"]

        new_step = dict(
            location=base,
            quantity=0,
            arrival=arrival,
            departure=arrival,
            layover_before=0,
            cumulated_driving_time=self.cumulated_driving_duration[driver]
            + travel_time,
            driving_time_before_layover=0,
        )
        self.solution_data[id_shift]["route"].append(new_step)

        self.cumulated_driving_duration[driver] = 0
        self.last_location[trailer]["location"] = base
        self.last_location[trailer][
            "time"
        ] += travel_time + self.instance.get_driver_property(
            driver, "minInterSHIFTDURATION"
        )
        self.current_shift[trailer]["day"] = None

    #
    def determine_quantity(self, trailer, customer, arrival):
        """
        Determines a quantity to deliver to the customer
        The quantity is determined randomly, respecting the capacity condition
        The quantity is enough to cover the customer's demand for the next 24 hours
        """
        demand_1day = self.demand_1d(customer, arrival)
        hour_arrival = floor(arrival / 60)
        inventory_when_arrival = self.site_inventories[customer]["tank_quantity"][
            hour_arrival
        ]

        quantity_delivered = randint(
            floor(demand_1day),
            min(
                self.inventory_trailers[trailer],
                floor(
                    self.instance.get_customer_property(customer, "Capacity")
                    - inventory_when_arrival
                ),
            ),
        )
        return quantity_delivered

    def determine_max_quantity(self, trailer, customer, arrival):
        hour_arrival = floor(arrival / 60)
        inventory_when_arrival = self.site_inventories[customer]["tank_quantity"][
            hour_arrival
        ]

        quantity_delivered = min(
            self.inventory_trailers[trailer],
            floor(
                self.instance.get_customer_property(customer, "Capacity")
                - inventory_when_arrival
            ),
        )
        return quantity_delivered

from .Greedy import Greedy
from .RouteLabel import RouteLabel
from ..core import Solution
from pytups import SuperDict
from random import shuffle
from collections import OrderedDict, defaultdict
import pickle
from math import floor
from statistics import mean


class RoutesGenerator:
    __slots__ = [
        "instance",
        "horizon",
        "nb_customers",
        "nb_sources",
        "nb_drivers",
        "max_dist_cost",
        "max_tmp_cost",
        "max_trailer_capacities",
        "max_driving_durations",
    ]

    def __init__(self, instance):
        self.instance = instance
        self.horizon = self.instance.get_horizon()
        self.nb_customers = self.instance.get_number_customers()
        self.nb_sources = self.instance.get_number_sources()
        self.nb_drivers = self.instance.get_number_drivers()

        self.max_dist_cost = max(
            self.instance.get_property("trailers", "DistanceCost").values()
        )
        self.max_tmp_cost = max(
            self.instance.get_property("drivers", "TimeCost").values()
        )
        self.max_trailer_capacities = max(
            self.instance.get_property("trailers", "Capacity").values()
        )
        self.max_driving_durations = max(
            self.instance.get_property("drivers", "maxDrivingDuration").values()
        )

    def generate_initial_routes(
        self,
        methods=None,
        unique=False,
        nb_random=0,
        nb_select_at_random_greedy=0,
    ):
        """
        Generates a list of initial routes from several methods
        :return: A list of RouteLabel elements
        """
        if methods is None:
            methods = ["shortestRoutes", "RST", "FromForecast", "Reversed"]

        initial_routes = []
        (
            routes_from_greedy,
            greedy_solution,
            value_greedy,
            nb_greedy,
        ) = self.get_routes_from_greedy(
            unique=True, nb_select_at_random=nb_select_at_random_greedy
        )
        initial_routes += routes_from_greedy

        if unique:
            tmp = []
            for route in initial_routes:
                if route.visited not in [unique.visited for unique in tmp]:
                    tmp.append(route)
            initial_routes = tmp

        tmp = []
        for route in initial_routes:
            final = []
            current_trip = []
            for step in route.visited:
                if self.is_source(step[0]) or self.is_base(step[0]):
                    current_trip.append(step)
                    if len(current_trip) > 2:
                        intermediaries = [k[0] for k in current_trip[1:-1]]
                        current_trip = self.get_shortest_paths(
                            start_location=current_trip[0][0],
                            end_location=current_trip[-1][0],
                            max_length=None,
                            max_visits=1,
                            max_trips=0,
                            intermediaries=intermediaries,
                            quantities=None,
                            return_all=False,
                        )[0].visited
                    final += current_trip[:-1]
                    current_trip = [step]
                elif self.is_customer(step[0]):
                    current_trip.append(step)
            final += current_trip

            route.visited = final
            route.update_label_time()
            route.update_label()
            tmp.append(route)
        initial_routes = tmp

        if "FromClusters" in methods:
            routes = self.generate_from_clusters()
            initial_routes += routes
        if "FromForecast" in methods:
            routes = self.generate_from_forecast()
            initial_routes += routes
        if "shortestRoutes" in methods:
            routes = self.get_shortest_paths()
            initial_routes += routes
        if "RST" in methods:
            routes = self.get_random_routes_from_shortest_trips(nb_random)
            initial_routes += routes

        if "Reversed" in methods:
            initial_routes += self.reversed_routes(initial_routes)

        if unique:
            routes = []
            for route in initial_routes:
                if route.visited not in [unique.visited for unique in routes]:
                    routes.append(route)
        else:
            routes = initial_routes

        return routes, nb_greedy, value_greedy, greedy_solution

    def get_routes_from_greedy(self, unique=True, nb_select_at_random=0):
        """
        Runs the Greedy algorithm and transforms the output routes into RouteLabel elements
        :param unique: if True, doesn't allow duplicate routes
        :param nb_select_at_random: if != 0, the method also runs a randomized version of Greedy
        :return: - A list of routes
                 - The solution of the non randomized greedy algorithm
                 - The value of the objective for the non randomized greedy algorithm
                 - The number of routes generated from the non-randomized greedy algorithm
        """
        routes = []
        select_at_random_list = [False] + [True] * nb_select_at_random
        value_obj = None
        greedy_nr_solution = None
        nb_greedy = 0

        for select_at_random in select_at_random_list:
            greedy_model = Greedy(self.instance)
            greedy_model.select_at_random = select_at_random
            greedy_model.solve(None)

            greedy_solution = greedy_model.solution
            greedy_solution = Solution(OrderedDict(greedy_solution.get_shifts_dict()))

            if not select_at_random:
                value_obj = greedy_model.get_objective()
                greedy_nr_solution = greedy_model.solution
                greedy_nr_solution = Solution(
                    OrderedDict(greedy_nr_solution.get_shifts_dict())
                )
                nb_greedy = greedy_nr_solution.nb_shifts()

            for shift in greedy_solution.get_all_shifts():
                label = RouteLabel(
                    origin="FG", instance=self.instance, visited=[[0, 0]]
                )
                driving_duration = 0
                cost = 0
                for step in shift["route"][1:]:
                    location = step["location"]
                    travel_time = self.instance.get_time_between(
                        label.visited[-1][0], location
                    )
                    dist = self.instance.get_distance_between(
                        label.visited[-1][0], location
                    )
                    setup_time = 0
                    if self.is_customer_or_source(location):
                        setup_time = self.instance.get_location_property(
                            location, "setupTime"
                        )
                    total_time = label.visited[-1][1] + travel_time + setup_time
                    driving_duration += travel_time
                    cost += (
                        setup_time + travel_time
                    ) * self.max_tmp_cost + dist * self.max_dist_cost
                    label.insert_at_the_end(location, total_time)
                label.cost = cost
                label.driving_duration = driving_duration
                if select_at_random:
                    label.origin += "-R"
                if unique and label.visited not in [route.visited for route in routes]:
                    routes.append(label)
                elif not unique:
                    routes.append(label)
        return routes, greedy_nr_solution, value_obj, nb_greedy

    def get_random_routes_from_shortest_trips(self, nb_routes, max_visits=2):
        """Generates randomized routes using the generation of shortest possible trips between two locations"""
        offset_customer = 1 + self.nb_sources
        shortest_trips = []

        for source_start in self.instance.get_id_sources():
            for source_arr in self.instance.get_id_sources():
                shortest_trips += self.get_shortest_paths(
                    source_start, source_arr, None, max_visits=1, max_trips=1
                )

        unique_shortest_trips = []
        for trip in shortest_trips:
            if trip.visited not in [unique.visited for unique in unique_shortest_trips]:
                unique_shortest_trips.append(trip)
        shortest_trips = unique_shortest_trips
        del unique_shortest_trips

        routes = []
        for i in range(nb_routes):
            remaining_trips = shortest_trips.copy()
            shuffle(remaining_trips)

            first_trip = remaining_trips[0]

            label = RouteLabel(
                origin="RST",
                instance=self.instance,
                cost=first_trip.cost,
                driving_duration=first_trip.driving_duration,
                visited=[[0, 0]] + first_trip.visited,
            )

            dist = self.instance.get_distance_between(0, first_trip.visited[0][0])
            time = self.instance.get_time_between(0, first_trip.visited[0][0])
            label.cost += dist * self.max_dist_cost + time * self.max_tmp_cost

            for j in range(len(label.visited) - 1):
                label.visited[j + 1][1] = label.visited[j + 1][1] + time

            del remaining_trips[0]

            while len(remaining_trips) != 0:
                trip = remaining_trips[0]
                time_to_base = self.instance.get_time_between(trip.visited[-1][0], 0)
                if (
                    label.driving_duration + trip.driving_duration + time_to_base
                    > self.max_driving_durations
                ):
                    del remaining_trips[0]
                    continue
                if label.visited[-1][0] != trip.visited[0][0]:
                    del remaining_trips[0]
                    remaining_trips.append(trip)
                    continue

                previous_visited_locations = [k[0] for k in label.visited]
                locations_current_trip = [k[0] for k in trip.visited]
                all_locations = previous_visited_locations + locations_current_trip
                if (
                    max(
                        [
                            all_locations.count(location)
                            for location in range(
                                offset_customer, 1 + self.nb_sources + self.nb_customers
                            )
                        ]
                    )
                    > max_visits
                ):
                    del remaining_trips[0]
                    continue

                total_driving_duration = label.driving_duration + trip.driving_duration
                label.cost = label.cost + trip.cost
                label.driving_duration = total_driving_duration
                time_trip = label.visited[-1][1]
                updated_visits = [
                    (visit[0], visit[1] + time_trip) for visit in trip.visited[1:]
                ]
                label.visited += updated_visits
                del remaining_trips[0]

            last_location = label.visited[-1][0]
            dist = self.instance.get_distance_between(last_location, 0)
            time = self.instance.get_time_between(last_location, 0)
            cost = dist * self.max_dist_cost + time * self.max_tmp_cost
            label.cost += cost
            label.driving_duration += time
            label.insert_at_the_end(0, label.visited[-1][1] + time)
            routes.append(label)
        return routes

    def generate_from_forecast(self):
        routes = []
        run_outs = dict()

        for day in range(self.horizon // 24 + 1):
            run_outs[day] = []

        last_deliveries = dict()
        for customer in self.instance.get_id_customers():
            last_deliveries[customer] = dict(
                hour=0,
                quantity=self.instance.get_customer_property(
                    customer, "InitialTankQuantity"
                ),
            )

        for customer in self.instance.get_id_customers():
            day_last_possible_visit = self.day_last_possible_visit(
                customer, last_deliveries
            )
            if day_last_possible_visit is not None:
                run_outs[day_last_possible_visit].append(customer)

        for day in run_outs.keys():
            shifts_day = SuperDict()
            id_shift = 0
            for customer in run_outs[day]:

                if len(shifts_day) == 0:

                    label = RouteLabel("FF", self.instance)
                    label.insert_location(customer, 1)
                    id_shift += 1
                    shifts_day[id_shift] = label

                    forecast = self.instance.get_customer_property(customer, "Forecast")
                    hour_last_delivery = last_deliveries[customer]["hour"]
                    last_deliveries[customer]["hour"] = 24 * day
                    last_deliveries[customer]["quantity"] += self.forecast_1day(
                        customer
                    ) - sum(
                        forecast[hour_last_delivery : last_deliveries[customer]["hour"]]
                    )

                    day_last_possible_visit = self.day_last_possible_visit(
                        customer, last_deliveries
                    )
                    if day_last_possible_visit is not None:
                        if run_outs.get(day_last_possible_visit, None) is None:
                            run_outs[day_last_possible_visit] = []
                        run_outs[day_last_possible_visit].append(customer)
                    continue

                min_increase_cost = None
                argmin_shift = None
                argmin_position = None

                for id_shift in shifts_day:
                    shift = shifts_day[id_shift]
                    for position in range(1, len(shift.visited) - 1):
                        if shift.breaks_constraints_to_insert(customer, position):
                            continue
                        increase_cost = (
                            shift.get_cost_with_inserted(customer, position)
                            - shift.cost
                        )
                        if argmin_position is None:
                            min_increase_cost = increase_cost
                            argmin_shift = id_shift
                            argmin_position = position
                        elif increase_cost < min_increase_cost:
                            min_increase_cost = increase_cost
                            argmin_shift = id_shift
                            argmin_position = position
                if argmin_position is not None:
                    checked_shift = shifts_day[argmin_shift].copy()
                    checked_shift.insert_location(customer, argmin_position)

                    position_source, source, need_refill = self.check_need_refill(
                        checked_shift
                    )
                    while position_source is not None:
                        checked_shift.insert_location(source, position_source)
                        position_source, source = self.check_need_refill(checked_shift)

                    if (
                        position_source is None and not need_refill
                    ) or position_source is not None:
                        shifts_day[argmin_shift].insert_location(
                            customer, argmin_position
                        )
                        if position_source is not None:
                            (
                                position_source,
                                source,
                                need_refill,
                            ) = self.check_need_refill(shifts_day[argmin_shift])
                            while position_source is not None:
                                shifts_day[argmin_shift].insert_location(
                                    source, position_source
                                )
                                position_source, source = self.check_need_refill(
                                    shifts_day[argmin_shift]
                                )
                else:
                    label = RouteLabel("FF", self.instance)
                    label.insert_location(customer, 1)
                    id_shift += 1
                    shifts_day[id_shift] = label

                hour_last_delivery = last_deliveries[customer]["hour"]
                forecast = self.instance.get_customer_property(customer, "Forecast")
                last_deliveries[customer]["hour"] = 24 * day
                last_deliveries[customer]["quantity"] += self.forecast_1day(
                    customer
                ) - sum(
                    forecast[hour_last_delivery : last_deliveries[customer]["hour"]]
                )
                day_last_possible_visit = self.day_last_possible_visit(
                    customer, last_deliveries
                )
                if day_last_possible_visit is not None:
                    run_outs[day_last_possible_visit].append(customer)
            routes += shifts_day.values_l()
        return routes

    def get_shortest_paths(
        self,
        start_location=0,
        end_location=0,
        max_length=None,
        max_visits=2,
        max_trips=5,
        intermediaries=None,
        quantities=None,
        return_all=True,
    ):
        """
        Applies a dynamic shortest path algorithm between two locations
        :param start_location:
        :param end_location:
        :param max_length: The maximum length of the path
        :param max_visits: The maximum number of visit at each customer
        :param max_trips: The maximum number of visit at a source + 1
        :param intermediaries: The locations that can be visited
        :param quantities: The quantities delivered at each customer if visited
        :param return_all: If False, returns the best possible route. If True, returns all the generated routes
        :return: a list of RouteLabel
        """
        if max_length is None:
            max_length = max_visits * self.nb_customers + max_trips
        if intermediaries is None:
            intermediaries = list(self.instance.get_id_sources()) + list(
                self.instance.get_id_customers()
            )

        table = [dict() for _ in range(max_length)]

        for i in intermediaries:
            dist = self.instance.get_distance_between(start_location, i)
            time = self.instance.get_time_between(start_location, i)
            cost_to = dist * self.max_dist_cost + time * self.max_tmp_cost
            driving_duration = time
            remaining = self.max_trailer_capacities
            if self.is_customer(i) and quantities is None:
                remaining = (
                    self.max_trailer_capacities
                    - self.instance.get_customer_property(i, "MinOperationQuantity")
                )
                total_time = time + self.instance.get_location_property(i, "setupTime")
            elif self.is_customer(i) and quantities is not None:
                remaining = self.max_trailer_capacities - quantities[i]
                total_time = time + self.instance.get_location_property(i, "setupTime")
            else:  # i is a source
                total_time = time + self.instance.get_location_property(i, "setupTime")
            departure = 0
            if self.is_source(start_location):
                departure = self.instance.get_location_property(
                    start_location, "setupTime"
                )
            label = RouteLabel(
                origin="SP",
                instance=self.instance,
                cost=cost_to,
                driving_duration=driving_duration,
                visited=[[start_location, departure], [i, total_time + departure]],
                remaining=remaining,
            )
            table[0][i] = label

        for length in range(1, max_length):
            for location in intermediaries:
                time_to_base = self.instance.get_distance_between(location, 0)
                min_cost = None
                argmin_cost = None

                for previous_location in intermediaries:
                    if (
                        table[length - 1].get(previous_location, None) is None
                        or previous_location == location
                    ):
                        continue
                    visited_locations = [
                        k[0] for k in table[length - 1][previous_location].visited
                    ]
                    if (
                        self.is_source(location)
                        and visited_locations.count(location) >= max_trips - 1
                    ):
                        continue
                    if (
                        self.is_customer(location)
                        and visited_locations.count(location) >= max_visits
                    ):
                        continue
                    time_travel = self.instance.get_time_between(
                        previous_location, location
                    )
                    if (
                        table[length - 1][previous_location].driving_duration
                        + time_travel
                        + time_to_base
                        > self.max_driving_durations
                    ):
                        continue
                    if quantities is None:
                        if self.is_customer(location):
                            min_quantity = max(
                                self.instance.get_customer_property(
                                    location, "MinOperationQuantity"
                                ),
                                self.forecast_1day(location),
                            )
                        else:
                            min_quantity = None
                    else:
                        min_quantity = quantities[location]
                    if min_quantity is not None:
                        if (
                            table[length - 1][previous_location].remaining_quantity
                            < min_quantity
                        ):
                            continue

                    dist = self.instance.get_distance_between(
                        previous_location, location
                    )
                    time = self.instance.get_time_between(previous_location, location)
                    if self.is_customer_or_source(location):
                        setup_time = self.instance.get_location_property(
                            location, "setupTime"
                        )
                    cost = (
                        dist * self.max_dist_cost
                        + (time + setup_time) * self.max_tmp_cost
                    )
                    if min_cost is None:
                        min_cost = table[length - 1][previous_location].cost + cost
                        argmin_cost = previous_location
                    elif min_cost > table[length - 1][previous_location].cost + cost:
                        min_cost = table[length - 1][previous_location].cost + cost
                        argmin_cost = previous_location

                if argmin_cost is not None:

                    time = self.instance.get_time_between(argmin_cost, location)
                    if self.is_customer_or_source(location):
                        setup_time = self.instance.get_location_property(
                            location, "setupTime"
                        )
                    total_time = (
                        table[length - 1][argmin_cost].visited[-1][1]
                        + time
                        + setup_time
                    )
                    label = RouteLabel(origin="SP", instance=self.instance)
                    label.cost = min_cost
                    label.driving_duration = (
                        table[length - 1][argmin_cost].driving_duration + time
                    )
                    label.visited = table[length - 1][argmin_cost].visited.copy()
                    label.insert_at_the_end(location, total_time)
                    if self.is_customer(location):
                        label.remaining_quantity = (
                            table[length - 1][argmin_cost].remaining_quantity
                            - min_quantity
                        )
                    elif self.is_source(location):
                        label.remaining_quantity = self.max_trailer_capacities

                    table[length][location] = label

        routes = []
        if return_all:
            for length in range(0, max_length):
                for location in intermediaries:
                    if table[length].get(location, None) is None:
                        continue
                    label = table[length][location].copy()

                    dist = self.instance.get_distance_between(location, end_location)
                    time = self.instance.get_time_between(location, end_location)
                    total_time = time
                    if self.is_source(end_location):
                        total_time = time + self.instance.get_location_property(
                            end_location, "setupTime"
                        )
                    cost = dist * self.max_dist_cost + time * self.max_tmp_cost

                    label.cost += cost
                    label.driving_duration += time
                    label.insert_at_the_end(
                        end_location, label.visited[-1][1] + total_time
                    )

                    routes.append(label)
        else:
            kept_label = None
            for length in range(max_length - 1, -1, -1):
                for location in intermediaries:
                    if table[length].get(location, None) is None:
                        continue
                    label = table[length][location].copy()

                    if kept_label is not None:
                        if (
                            label.nb_customers_in_label()
                            < kept_label.nb_customers_in_label()
                        ):
                            continue

                    dist = self.instance.get_distance_between(location, end_location)
                    time = self.instance.get_time_between(location, end_location)
                    total_time = time
                    if self.is_source(end_location):
                        total_time = time + self.instance.get_location_property(
                            end_location, "setupTime"
                        )
                    cost = dist * self.max_dist_cost + time * self.max_tmp_cost

                    label.cost += cost
                    label.driving_duration += time
                    label.insert_at_the_end(
                        end_location, label.visited[-1][1] + total_time
                    )

                    if kept_label is None:
                        kept_label = label
                    elif kept_label.has_higher_cost_than(label):
                        kept_label = label
            return [kept_label]
        return routes

    def generate_new_routes(self, artificial_quantities, make_clusters):
        """
        Generates new routes from a set of ideal deliveries
        :param artificial_quantities: A dictionary whose keys are pairs (index_customer, hour) and whose values are
            pulp variables ArtQuant(i, h) with non-zero values indicating that it would be ideal to deliver the
            quantity value(ArtQuant(i, h)) to customer i at hour h
        :param make_clusters: if True, will separate the customers into clusters before
            creating the shifts that visit only customers of the same cluster
        :return: A list of shifts with defined departure times
        """
        routes = []
        offset_customer = 1 + self.nb_sources
        max_visits = 1
        nb_distinct_routes = 20
        nb_generated_routes = 500
        min_range_day = -0.75
        max_range_day = 0.76
        interval = 0.25

        delivery_days = defaultdict(list)
        for (i, h), quantity in artificial_quantities.items():
            delivery_days[floor(h / 24)].append(dict(client=i, quantity=quantity))

        for day, item in delivery_days.items():
            quantities = {
                item[i]["client"]: -item[i]["quantity"] for i in range(len(item))
            }
            shifts_or_routes = []

            for start in [0] + list(self.instance.get_id_sources()):
                for end in [0] + list(self.instance.get_id_sources()):
                    shifts_or_routes += self.get_shortest_paths(
                        start,
                        end,
                        None,
                        1,
                        1,
                        list(set([item[i]["client"] for i in range(len(item))])),
                        quantities,
                    )
            shifts_or_routes_copy = shifts_or_routes.copy()

            for trip in shifts_or_routes_copy:
                if trip.visited[0][0] == 0 and trip.visited[-1][0] == 0:
                    for dd in range(
                        floor(max(min_range_day, -day) / interval),
                        floor(min(max_range_day, self.horizon // 24 - day) / interval),
                    ):
                        trip_copy = trip.copy()
                        trip_copy.start = (day + dd * interval) * 24
                        trip_copy.origin = "NR"
                        routes.append(trip_copy)
                    shifts_or_routes.remove(trip)

            k = 0
            added_routes = 0
            #################
            while added_routes < nb_distinct_routes and k < nb_generated_routes:
                k += 1
                remaining_trips = pickle.loads(pickle.dumps(shifts_or_routes, -1))
                shuffle(remaining_trips)

                first_trip = remaining_trips[0]
                if first_trip.visited[0][0] != 0:
                    label = RouteLabel(
                        origin="NR",
                        instance=self.instance,
                        cost=first_trip.cost,
                        driving_duration=first_trip.driving_duration,
                        visited=[[0, 0]] + first_trip.visited,
                    )
                    dist = self.instance.get_distance_between(
                        0, first_trip.visited[0][0]
                    )
                    time = self.instance.get_time_between(0, first_trip.visited[0][0])
                    label.cost += dist * self.max_dist_cost + time * self.max_tmp_cost

                    for j in range(len(label.visited) - 1):
                        label.visited[j + 1][1] = label.visited[j + 1][1] + time
                else:
                    label = first_trip.copy()

                del remaining_trips[0]
                if label.visited[-1][0] == 0:
                    already_in = False
                    if not already_in:
                        for dd in range(
                            floor(max(min_range_day, -day) / interval),
                            floor(
                                min(max_range_day, self.horizon // 24 - day) / interval
                            ),
                        ):
                            label_copy = label.copy()
                            label_copy.start = (day + dd * interval) * 24
                            label_copy.origin = "NR"
                            routes.append(label_copy)
                            added_routes += 1
                    continue
                while len(remaining_trips) != 0:

                    trip = remaining_trips[0]

                    if trip.visited[-1][0] == 0:
                        time_to_base = 0
                    else:
                        time_to_base = self.instance.get_distance_between(
                            trip.visited[-1][0], 0
                        )

                    if (
                        label.driving_duration + trip.driving_duration + time_to_base
                        > self.max_driving_durations
                    ):
                        del remaining_trips[0]
                        continue

                    if label.visited[-1][0] != trip.visited[0][0]:
                        del remaining_trips[0]
                        continue

                    previous_visited_locations = [k[0] for k in label.visited]
                    locations_current_trip = [k[0] for k in trip.visited]
                    all_locations = previous_visited_locations + locations_current_trip
                    if (
                        max(
                            [
                                all_locations.count(location)
                                for location in range(
                                    offset_customer,
                                    1 + self.nb_sources + self.nb_customers,
                                )
                            ]
                        )
                        > max_visits
                    ):
                        del remaining_trips[0]
                        continue
                    total_driving_duration = (
                        label.driving_duration + trip.driving_duration
                    )
                    label.cost = label.cost + trip.cost
                    label.driving_duration = total_driving_duration
                    time_trip = label.visited[-1][1]
                    updated_visits = [
                        [visit[0], visit[1] + time_trip] for visit in trip.visited[1:]
                    ]
                    label.visited += updated_visits
                    del remaining_trips[0]

                    if label.visited[-1][0] == 0:
                        already_in = False
                        if not already_in:
                            for dd in range(
                                floor(max(min_range_day, -day) / interval),
                                floor(
                                    min(max_range_day, self.horizon // 24 - day)
                                    / interval
                                ),
                            ):
                                label_copy = label.copy()
                                label_copy.start = (day + dd * interval) * 24
                                label_copy.origin = "NR"
                                routes.append(label_copy)
                                added_routes += 1
                        break

                last_location = label.visited[-1][0]
                if last_location != 0:
                    dist = self.instance.get_distance_between(last_location, 0)
                    time = self.instance.get_time_between(last_location, 0)
                    cost = dist * self.max_dist_cost + time * self.max_tmp_cost
                    label.cost += cost
                    label.driving_duration += time
                    label.insert_at_the_end(0, label.visited[-1][1] + time)
                label.origin = "NR"
                already_in = False
                if not already_in:
                    for dd in range(
                        floor(max(min_range_day, -day) / interval),
                        floor(min(max_range_day, self.horizon // 24 - day) / interval),
                    ):
                        label_copy = label.copy()
                        label_copy.start = (day + dd * interval) * 24
                        routes.append(label_copy)
                        added_routes += 1
        #################
        shuffle(routes)

        if make_clusters:
            delivery_days_copy = pickle.loads(pickle.dumps(delivery_days, -1))

            for day in delivery_days_copy:
                clients = [delivery["client"] for delivery in delivery_days[day]] + [
                    delivery["client"] for delivery in delivery_days[day + 1]
                ]
                new_routes = self.generate_from_clusters(clients)

                for route in new_routes:
                    for dd in range(
                        floor(max(min_range_day, -day) / interval),
                        floor(min(max_range_day, self.horizon // 24 - day) / interval),
                    ):
                        label_copy = route.copy()
                        label_copy.start = (day + dd * interval) * 24
                        label_copy.origin = "NR-c-2d"
                        routes.append(label_copy)

                    for dd in range(
                        floor(max(min_range_day, -(day + 1)) / interval),
                        floor(
                            min(max_range_day, self.horizon // 24 - (day + 1))
                            / interval
                        ),
                    ):
                        label_copy = route.copy()
                        label_copy.start = (day + 1 + dd * interval) * 24
                        label_copy.origin = "NR-c-2d"
                        routes.append(label_copy)
                clients = (
                    [delivery["client"] for delivery in delivery_days[day]]
                    + [delivery["client"] for delivery in delivery_days[day + 1]]
                    + [delivery["client"] for delivery in delivery_days[day + 2]]
                )
                new_routes = self.generate_from_clusters(clients)

                for route in new_routes:
                    for dd in range(
                        floor(max(min_range_day, -day) / interval),
                        floor(min(max_range_day, self.horizon // 24 - day) / interval),
                    ):
                        label_copy = route.copy()
                        label_copy.start = (day + dd * interval) * 24
                        label_copy.origin = "NR-c-3d"
                        routes.append(label_copy)

                    for dd in range(
                        floor(max(min_range_day, -(day + 1)) / interval),
                        floor(
                            min(max_range_day, self.horizon // 24 - (day + 1))
                            / interval
                        ),
                    ):
                        label_copy = route.copy()
                        label_copy.start = (day + 1 + dd * interval) * 24
                        label_copy.origin = "NR-c-3d"

                    for dd in range(
                        floor(max(min_range_day, -(day + 2)) / interval),
                        floor(
                            min(max_range_day, self.horizon // 24 - (day + 2))
                            / interval
                        ),
                    ):
                        label_copy = route.copy()
                        label_copy.start = (day + 2 + dd * interval) * 24
                        label_copy.origin = "NR-c-3d"

        return routes

    def create_clusters(self, points=None, eps_div=2):
        """
        Separates the given points into clusters
        :return: A dictionary whose keys are the indices of the clusters and whose values are list of points
        For example: {1: [2, 3, 6],
                      2: [4, 5, 7]}
        """
        mean_distance_to_base = mean(
            [
                self.instance.get_distance_between(0, j)
                for j in range(1, self.instance.get_number_locations())
            ]
        )
        eps = mean_distance_to_base / eps_div

        clusters = dict()
        id_next_cluster = 0
        if points is None:
            points = list(self.instance.get_id_customers())

        for point in points:
            possible_clusters = set()
            for id_cluster, cluster in clusters.items():
                forecast1day_cluster = sum(
                    [self.forecast_1day(customer) for customer in cluster]
                )

                for point_cluster in cluster:
                    if self.instance.get_distance_between(point, point_cluster) > eps:
                        continue
                    if (
                        forecast1day_cluster + self.forecast_1day(point)
                        <= self.max_trailer_capacities
                    ):
                        possible_clusters.add(id_cluster)
            if len(possible_clusters) == 0:
                clusters[id_next_cluster] = [point]
                id_next_cluster += 1
            else:
                argmin_avg = None
                min_avg = None

                for id_cluster in possible_clusters:
                    avg = mean(
                        [
                            self.instance.get_distance_between(point, point_cluster)
                            for point_cluster in clusters[id_cluster]
                        ]
                    )
                    if min_avg is None:
                        min_avg = avg
                        argmin_avg = id_cluster
                    elif avg < min_avg:
                        min_avg = avg
                        argmin_avg = id_cluster
                clusters[argmin_avg].append(point)
        tmp_clusters = []

        for cluster in clusters.values():
            if len(cluster) > 5:
                tmp_clusters += list(
                    self.create_clusters(cluster, eps_div * 2).values()
                )
            else:
                tmp_clusters.append(cluster)
        clusters = dict(enumerate(tmp_clusters))

        return clusters

    def generate_from_clusters(self, points=None):
        """
        Generates routes based on a clustering of all the locations
        :return: a list of RouteLabel
        """
        clusters = self.create_clusters(points=points)
        routes = []

        for cluster in clusters.values():
            routes += self.get_shortest_paths(
                start_location=0,
                end_location=0,
                max_length=None,
                max_visits=1,
                max_trips=2,
                intermediaries=cluster + list(self.instance.get_id_sources()),
            )
        def_routes = []

        for route in routes.copy():
            keep = True
            for route2 in def_routes.copy():
                if not route.delivers_same_locations_as(route2):
                    continue
                if route2.has_higher_cost_than(route):
                    def_routes.remove(route2)
                else:
                    keep = False

            if keep:
                route.origin = "FC"
                def_routes.append(route)
        return def_routes

    def check_need_refill(self, label):
        """
        Checks the trailer of the route needs to load product at some point on the route to avoid running out
        :return: None None, False if no refill needed
                 If refill needed, returns:
                    - the position where the source should be inserted
                    - the closest source to insert at that position
                    - True
        """
        position = None
        remaining = self.max_trailer_capacities

        for i, step in enumerate(label.visited):
            if self.is_source(step[0]):
                remaining = self.max_trailer_capacities
            elif self.is_customer(step[0]):
                remaining -= self.forecast_1day(step[0])
            if remaining < 0 and position is None:
                position = i
        if position is None:
            return None, None, False
        min_cost_insertion = None
        min_position_insertion = None
        min_source_insertion = None

        for j in range(max(1, position - 1), position):
            for source in self.instance.get_id_sources():
                if not label.breaks_constraints_to_insert(source, j):
                    cost_insertion = label.get_cost_with_inserted(source, j)
                    if min_cost_insertion is None:
                        min_cost_insertion = cost_insertion
                        min_position_insertion = j
                        min_source_insertion = source
                    if cost_insertion < min_cost_insertion:
                        min_cost_insertion = cost_insertion
                        min_position_insertion = j
                        min_source_insertion = source
        return min_position_insertion, min_source_insertion, True

    def reversed_routes(self, routes):
        """
        Reverses the location in the given routes
        :return: a list of RouteLabel
        """
        reversed_routes = []
        for route in routes:
            reversed_label = RouteLabel(
                origin=route.origin + "_REV", instance=self.instance
            )
            reversed_route = [k[0] for k in route.visited]
            reversed_route.reverse()
            remaining = self.max_trailer_capacities
            driving_duration = 0
            last_location_visited = 0
            cost = 0

            reversed_label.visited = [[0, 0]]

            for location in reversed_route[1:]:
                if self.is_customer(location) and remaining < max(
                    self.instance.get_customer_property(
                        location, "MinOperationQuantity"
                    ),
                    self.forecast_1day(location),
                ):

                    continue

                travel_time = self.instance.get_time_between(
                    last_location_visited, location
                )
                time_to_base = self.instance.get_time_between(location, 0)
                dist = self.instance.get_distance_between(
                    last_location_visited, location
                )
                setup_time = 0
                if self.is_source(location):
                    setup_time = self.instance.get_location_property(
                        location, "setupTime"
                    )
                    remaining = self.max_trailer_capacities
                elif self.is_customer(location):
                    setup_time = self.instance.get_location_property(
                        location, "setupTime"
                    )
                    remaining -= max(
                        self.instance.get_customer_property(
                            location, "MinOperationQuantity"
                        ),
                        self.forecast_1day(location),
                    )

                if (
                    driving_duration + travel_time + time_to_base
                    > self.max_driving_durations
                ):
                    continue

                last_location_visited = location
                driving_duration += travel_time
                cost += (
                    setup_time + travel_time
                ) * self.max_tmp_cost + dist * self.max_dist_cost
                reversed_label.insert_at_the_end(
                    location, reversed_label.visited[-1][1] + travel_time + setup_time
                )

            reversed_label.cost = cost
            reversed_label.driving_duration = driving_duration
            reversed_routes.append(reversed_label)
        return reversed_routes

    def forecast_1day(self, customer):
        """Returns the average quantity that the customer consumes in one day"""
        forecast = self.instance.get_customer_property(customer, "Forecast")
        sum_f = max([sum(forecast[i : i + 23]) for i in range(0, self.horizon - 23)])
        return sum_f / 2

    def day_last_possible_visit(self, customer, inventories):
        """Returns the last possible day to visit the given customer to avoid a stock-out"""
        # Inventories : {customer : {hour: , remaining_quantity: }
        forecast = self.instance.get_customer_property(customer, "Forecast")

        inventory = inventories.get(customer, None)
        if inventory is None:
            remaining_quantity = self.instance.get_customer_property(
                customer, "InitialTankQuantity"
            )
        else:
            remaining_quantity = inventory["quantity"]

        instant = inventory["hour"]
        while (
            instant < self.horizon - 1
            and remaining_quantity - sum(forecast[inventory["hour"] : instant]) > 0
        ):
            instant += 1
        if remaining_quantity - sum(forecast[inventory["hour"] : instant]) <= 0:
            day = floor(max(0, instant - 1) / 24)
            if day == inventory["hour"] // 24:
                day += 1
            return day
        return None

    def is_base(self, location):
        return self.instance.is_base(location)

    def is_source(self, location):
        return self.instance.is_source(location)

    def is_customer(self, location):
        return self.instance.is_customer(location)

    def is_customer_or_source(self, location):
        return self.instance.is_customer_or_source(location)

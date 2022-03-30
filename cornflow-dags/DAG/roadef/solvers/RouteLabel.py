import pickle


class RouteLabel:
    __slots__ = ["origin", "instance", "cost", "driving_duration", "visited",
                 "remaining_quantity", "over", "start", "max_dist_cost",
                 "max_tmp_cost", "max_trailer_capacities", "max_driving_durations"]

    def __init__(
        self,
        origin,
        instance,
        cost=0,
        driving_duration=0,
        visited=None,
        remaining=0,
        over=False,
    ):
        self.origin = origin
        self.instance = instance
        self.cost = cost
        self.driving_duration = driving_duration
        self.visited = visited
        if self.visited is None:
            self.visited = [[0, 0], [0, 0]]
        self.remaining_quantity = remaining
        self.over = over
        self.start = None

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

    def get_label_with_start(self, start):
        """ Returns the label with the addition of a starting hour """
        self.start = start
        return self

    def insert_location(self, location, position):
        " Inserts a new stop in the route at given position "
        self.visited.insert(position, [location, 0])
        self.update_label_time()
        self.update_label()

    def insert_at_the_end(self, location, time):
        """ Adds a stop at the end of the route """
        self.visited.append([location, time])

    def breaks_constraints_to_insert(self, customer, position):
        """ Returns true if adding the customer at the given position in the route breaks duration constraints """
        new_label = self.copy()
        new_label.insert_location(customer, position)
        new_label.update_label()
        breaks_constraints = False
        if new_label["driving_duration"] > self.max_driving_durations:
            breaks_constraints = True
        return breaks_constraints

    def update_label_time(self):
        """ Updates the departure times at each step to keep the timeline coherent """
        for i in range(len(self.visited)):
            location = self.visited[i][0]
            if i == 0:
                self.visited[i][1] = 0
            else:
                travel_time = self.instance.get_time_between(
                    self.visited[i - 1][0], location
                )
                setup_time = 0
                if self.instance.is_customer_or_source(location):
                    setup_time = self.instance.get_location_property(
                        location, "setupTime"
                    )
                self.visited[i][1] = self.visited[i - 1][1] + travel_time + setup_time

    def update_label(self):
        """ Updates the cost and the driving duration of the route according to the list of operations """
        cost = 0
        driving_duration = 0
        for i in range(len(self.visited[1:])):
            location = self.visited[i + 1][0]
            previous_location = self.visited[i][0]

            if self.instance.is_customer_or_source(location):
                cost += (
                    self.instance.get_location_property(location, "setupTime")
                    + self.instance.get_time_between(previous_location, location)
                ) * self.max_tmp_cost
            elif self.instance.is_base(location):
                cost += (
                    self.instance.get_time_between(previous_location, location)
                    * self.max_tmp_cost
                )
            cost += (
                self.instance.get_distance_between(previous_location, location)
                * self.max_dist_cost
            )
            driving_duration += self.instance.get_time_between(
                previous_location, location
            )
        self.cost = cost
        self.driving_duration = driving_duration

    def copy(self):
        new_label = RouteLabel(
            self.origin,
            self.instance,
            self.cost,
            self.driving_duration,
            pickle.loads(pickle.dumps(self.visited, -1)),
            self.remaining_quantity,
            self.over,
        )
        return new_label

    def has_higher_cost_than(self, route):
        """ Returns True if self has higher cost than the parameter route """
        return self.cost > route.cost

    def has_same_cost_than(self, route):
        """ Returns True if self has same cost as the parameter route """
        return self.cost == route.cost

    def has_inferior_cost_than(self, route):
        """ Returns True if self has inferior cost than the parameter route """
        return self.cost < route.cost

    def is_longer_than(self, route):
        """ Returns True if self has higher driving duration than the parameter route """
        return self.driving_duration > route.driving_duration

    def is_shorter_than(self, route):
        """ Returns True if self has lower driving duration than the parameter route """
        return self.driving_duration < route.driving_duration

    def has_same_duration_as(self, route):
        """ Returns True if self has same driving duration as the parameter route """
        return self.driving_duration == route.driving_duration

    def delivers_same_locations_as(self, route):
        """ Returns True if the two routes deliver exactly the same customers and load at the same sources """
        self_customers_and_sources = set(
            [
                step[0]
                for step in self.visited
                if self.instance.is_customer(step[0])
                or self.instance.is_source(step[0])
            ]
        )
        route_customers_and_sources = set(
            [
                step[0]
                for step in route.visited
                if route.instance.is_customer(step[0])
                or route.instance.is_source(step[0])
            ]
        )
        return self_customers_and_sources == route_customers_and_sources

    def get_cost_with_inserted(self, customer, position):
        """ Returns the cost if the route if we inserted the given customer at the given position """
        new_label = self.copy()
        new_label.insert_location(customer, position)
        new_label.update_label()
        return new_label.cost

    def nb_customers_in_label(self):
        """ Returns the number of customers delivered on the route """
        customers = []
        for step in self.visited:
            if self.instance.is_customer(step[0]) and step[0] not in customers:
                customers.append(step[0])
        return len(list(set(customers)))

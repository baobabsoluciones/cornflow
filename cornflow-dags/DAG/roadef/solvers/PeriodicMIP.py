from .RoutesGenerator import RoutesGenerator
from .MIPModel import MIPModel
from collections import defaultdict, OrderedDict
from pytups import SuperDict, TupList
from datetime import datetime
import pulp as pl
import pickle
import json
import itertools
from cornflow_client.constants import STATUS_FEASIBLE, SOLUTION_STATUS_FEASIBLE


class PeriodicMIP(MIPModel):
    def __init__(self, instance, solution=None):
        super().__init__(instance, solution)
        self.log = ""
        self.solver = "Periodic MIP Model"
        self.routes_generator = RoutesGenerator(self.instance)
        self.range_hours = list(range(self.horizon))
        self.routes = dict()
        self.unused_routes = dict()
        self.value_greedy = None
        self.interval_routes = 6
        self.nb_routes = 1000
        self.start_time = datetime.now()
        self.start_time_string = datetime.now().strftime("%d.%m-%Hh%M")
        self.print_log = False
        self.save_results = False
        self.artificial_quantities = dict()
        self.limit_artificial_round = 0
        self.last_solution_round = -1
        self.Hmin = 0
        self.Hmax = self.horizon
        self.resolution_interval = 180
        self.resolve_margin = 48
        self.solution_greedy = None
        self.locations_in = dict()
        self.unique_locations_in = dict()
        self.hour_of_visit = dict()
        self.k_visit_hour = dict()
        self.nb_visits = dict()
        self.final_routes = None
        self.coef_part_inventory_conservation = 0.8
        self.coef_inventory_conservation = 1
        self.time_limit = 100000

        # Variables
        self.route_var = SuperDict()
        self.artificial_quantities_var = SuperDict()
        self.artificial_binary_var = SuperDict()
        self.inventory_var = SuperDict()
        self.quantity_var = SuperDict()
        self.trailer_quantity_var = SuperDict()

    def solve(self, config=None):
        self.start_time = datetime.now()
        self.start_time_string = datetime.now().strftime("%d.%m-%Hh%M")

        if config is None:
            config = dict()
        config = dict(config)

        self.time_limit = config.get("timeLimit", 100000)
        self.coef_inventory_conservation = config.get(
            "inventoryConservation", self.coef_inventory_conservation
        )
        self.coef_part_inventory_conservation = config.get(
            "partialInventoryConservation", self.coef_inventory_conservation
        )
        solver_name = self.get_solver(config)

        self.print_in_console("Started at: ", self.start_time_string)

        self.nb_routes = config.get("nb_routes_per_run", self.nb_routes)

        used_routes = dict()

        self.Hmin = 0
        self.Hmax = min(self.resolution_interval, self.horizon)
        while self.Hmin < self.horizon and self._get_remaining_time() > 0:
            self.print_in_console(
                f"=================== Hmin = {self.Hmin} ========================"
            )
            self.print_in_console(
                f"=================== Hmax = {self.Hmax} ========================"
            )
            current_round = 0

            new_routes = self.generate_initial_routes()
            self.routes = dict(list(self.routes.items()) + list(new_routes.items()))
            previous_value = None
            self.unused_routes = pickle.loads(pickle.dumps(new_routes, -1))

            self.print_in_console(
                "=================== ROUND 0 ========================"
            )
            self.print_in_console(
                "Initial empty solving at: ", datetime.now().strftime("%H:%M:%S")
            )

            config_first = dict(
                solver=solver_name,
                rel_gap=0.1,
                timeLimit=min(200.0, self._get_remaining_time()),
                msg=self.print_log,
            )
            config_first = self.get_solver_config(config_first, lib="pulp")

            def config_iteration(self):
                conf = dict(
                    solver=solver_name,
                    rel_gap=0.05,
                    timeLimit=min(100.0, self._get_remaining_time()),
                    msg=self.print_log,
                    warmStart=(current_round != 1),
                )
                return self.get_solver_config(conf, lib="pulp")

            solver = pl.getSolver(solver=solver_name, **config_first)
            used_routes, previous_value = self.solve_one_iteration(
                solver, used_routes, previous_value, current_round
            )
            current_round += 1

            while len(self.unused_routes) != 0 and self._get_remaining_time() > 0:
                self.print_in_console(
                    f"=================== ROUND {current_round} ========================"
                )
                solver = pl.getSolver(solver=solver_name, **config_iteration(self))

                used_routes, previous_value = self.solve_one_iteration(
                    solver, used_routes, previous_value, current_round
                )
                current_round += 1

            self.Hmax = min(self.Hmax + self.resolution_interval, self.horizon)
            self.Hmin += self.resolution_interval

        self.set_final_id_shifts()
        self.post_process()

        self.final_routes = used_routes
        self.print_in_console(used_routes)

        if self.save_results:
            with open(
                f"res/solution-schema-{self.start_time_string}-final.json", "w"
            ) as fd:
                json.dump(self.solution.to_dict(), fd)

        return dict(status=STATUS_FEASIBLE, status_sol=SOLUTION_STATUS_FEASIBLE)

    def solve_one_iteration(self, solver, used_routes, previous_value, current_round):
        if 0 < current_round <= self.limit_artificial_round + 1:
            self.generate_new_routes()
            self.artificial_quantities = dict()

        old_used_routes = pickle.loads(pickle.dumps(used_routes, -1))
        previous_routes_infos = [
            (shift["id_shift"], shift["trailer"], shift["driver"])
            for shift in self.solution.get_all_shifts()
        ]

        if current_round > 0:
            selected_routes = self.select_routes(self.nb_routes)
            used_routes = SuperDict({**used_routes, **selected_routes})
            self.initialize_parameters(used_routes)

        model = self.new_model(
            used_routes,
            previous_routes_infos,
            current_round <= self.limit_artificial_round,
        )
        status = model.solve(solver=solver)

        if status == 1:
            self.to_solution(model, used_routes, current_round)
            if current_round > self.limit_artificial_round:
                self.checkpoint_and_save(current_round)

        if status != 1 or current_round == 0:
            used_routes = old_used_routes
            return used_routes, None

        if not (
            previous_value is None
            or pl.value(model.objective) < previous_value
            or (
                (current_round > self.limit_artificial_round)
                and (self.last_solution_round <= self.limit_artificial_round)
            )
        ):
            return old_used_routes, previous_value

        keep = (
            self.route_var.vfilter(lambda v: pl.value(v) > 0.5)
            .keys_tl()
            .take(0)
            .to_dict(None)
            .vapply(lambda v: True)
        )

        used_routes = {
            r: route for r, route in used_routes.items() if keep.get(r, False)
        }

        if current_round > self.limit_artificial_round:
            previous_value = pl.value(model.objective)
        self.last_solution_round = current_round
        return used_routes, previous_value

    def generate_initial_routes(self):
        """
        Generates shifts from initial methods
        The generated shifts already have a departure time and respect the duration constraint
        :return: A dictionary whose keys are the indices of the shifts and whose values are instances of RouteLabel
        """
        # 'shortestRoutes', 'FromForecast', 'RST'
        (
            routes,
            nb_greedy,
            self.value_greedy,
            self.solution_greedy,
        ) = self.routes_generator.generate_initial_routes(
            methods=["FromClusters"],
            unique=True,
            nb_random=0,
            nb_select_at_random_greedy=0,
        )
        self.print_in_console("Value greedy: ", self.value_greedy)

        partial_interval_routes = self.interval_routes
        while nb_greedy * (self.horizon // partial_interval_routes) > 400:
            partial_interval_routes = 2 * partial_interval_routes

        routes_greedy = routes[0:nb_greedy]
        other_routes = routes[nb_greedy:]

        routes = [
            route.copy().get_label_with_start(start)
            for offset in range(0, partial_interval_routes, self.interval_routes)
            for route in routes_greedy
            for start in range(
                max(self.Hmin - 72, 0) + offset, self.Hmax, partial_interval_routes
            )
            if start + PeriodicMIP.duration_route(route) < self.Hmax
        ] + [
            route.copy().get_label_with_start(start)
            for offset in range(0, partial_interval_routes, self.interval_routes)
            for route in other_routes
            for start in range(
                max(self.Hmin - 72, 0) + offset, self.Hmax, partial_interval_routes
            )
            if start + PeriodicMIP.duration_route(route) < self.Hmax
        ]
        self.print_in_console(routes)

        self.nb_routes = max(
            self.nb_routes, nb_greedy * (self.horizon // partial_interval_routes)
        )
        self.print_in_console(f"Nb routes from initial generation: {len(routes)}")
        self.print_in_console(f"Nb routes per run: {self.nb_routes}")

        if len(self.routes) != 0:
            start_id = max(list(self.routes.keys())) + 1
        else:
            start_id = 0
        self.print_in_console(dict(enumerate(routes, start_id)))
        return dict(enumerate(routes, start_id))

    def generate_new_routes(self):
        """
        Generates new shifts based on the values of the artificial variables , i.e. based on the ideal deliveries
        :return: A dictionary whose keys are the indices of the shifts and whose values are instances of RouteLabel
        """
        self.print_in_console(
            "Generating new routes at: ", datetime.now().strftime("%H:%M:%S")
        )

        new_routes = self.routes_generator.generate_new_routes(
            self.artificial_quantities, make_clusters=True
        )

        new_routes = [
            route
            for route in new_routes
            if route.start + PeriodicMIP.duration_route(route) <= self.Hmax
        ]

        enumerated_new_routes = list(enumerate(new_routes, max(self.routes.keys()) + 1))

        self.print_in_console(f"Generated {len(enumerated_new_routes)} new routes")

        self.routes = OrderedDict(enumerated_new_routes + list(self.routes.items()))
        self.unused_routes = OrderedDict(
            enumerated_new_routes + list(self.unused_routes.items())
        )

    def new_model(self, used_routes, previous_routes_infos, artificial_variables):
        self.print_in_console(
            "Generating new model at: ", datetime.now().strftime("%H:%M:%S")
        )
        model = pl.LpProblem("Roadef", pl.LpMinimize)
        self.create_variables(used_routes, previous_routes_infos, artificial_variables)
        model = self.create_constraints(model, used_routes, artificial_variables)
        return model

    def create_variables(
        self, used_routes, previous_routes_infos, artificial_variables
    ):
        # Indices
        ind_td_routes = self.get_td_routes(used_routes)
        ind_customers_hours = self.get_customers_hours()

        # Initial quantities from previous solutions
        initial_quantities = dict()
        for r, route in self.solution.get_id_and_shifts():
            k = defaultdict(int)
            for step in route["route"]:
                if step["location"] == 0:
                    continue
                k[step["location"]] += 1
                initial_quantities[
                    (
                        step["location"],
                        r,
                        self.solution.get_shift_property(r, "trailer"),
                        k[step["location"]],
                    )
                ] = step["quantity"]

        # Variables : route
        self.route_var = pl.LpVariable.dicts("route", ind_td_routes, 0, 1, pl.LpBinary)
        previous_routes_infos_s = set(previous_routes_infos)
        for k, v in self.route_var.items():
            v.setInitialValue(k in previous_routes_infos_s)
            if self.routes[k[0]].start < self.Hmin - self.resolve_margin:
                v.fixValue()
        self.route_var = SuperDict(self.route_var)
        self.print_in_console("Var 'route'")

        # Variables : Artificial Quantity
        if artificial_variables:
            self.artificial_quantities_var = pl.LpVariable.dicts(
                "ArtificialQuantity", ind_customers_hours, None, 0
            )
            self.artificial_binary_var = pl.LpVariable.dicts(
                "ArtificialBinary", ind_customers_hours, 0, 1, pl.LpBinary
            )

            for i, h in ind_customers_hours:
                if h < self.Hmin - self.resolve_margin:
                    self.artificial_binary_var[i, h].setInitialValue(0)
                    self.artificial_binary_var[i, h].fixValue()
            self.artificial_quantities_var = SuperDict(self.artificial_quantities_var)
            self.artificial_binary_var = SuperDict(self.artificial_binary_var)
        else:
            self.artificial_quantities_var = SuperDict()
            self.artificial_binary_var = SuperDict()
        self.print_in_console("Var 'ArtificialQuantity'")

        # Variables : Inventory
        _capacity = lambda i: self.instance.get_customer_property(i, "Capacity")
        self.inventory_var = {
            (i, h): pl.LpVariable(f"Inventory{i, h}", 0, _capacity(i))
            for (i, h) in self.get_var_inventory_domain()
        }
        self.inventory_var = SuperDict(self.inventory_var)
        self.print_in_console("Var 'inventory'")

        # Variables : quantity
        for r, i, tr, k in self.get_var_quantity_s_domain(used_routes):
            self.quantity_var[i, r, tr, k] = pl.LpVariable(f"quantity{i, r, tr, k}", 0)
            if initial_quantities.get((i, r, tr, k), None) is None:
                continue
            self.quantity_var[i, r, tr, k].setInitialValue(
                initial_quantities[(i, r, tr, k)]
            )
            """if self.routes[r].start < self.Hmin - self.resolve_margin:
                self.variables["quantity"][(i, r, tr, k)].fixValue() """

        for r, i, tr, k in self.get_var_quantity_p_domain(used_routes):
            self.quantity_var[i, r, tr, k] = pl.LpVariable(
                f"quantity{i, r, tr, k}", upBound=0
            )
            if initial_quantities.get((i, r, tr, k), None) is None:
                continue
            self.quantity_var[i, r, tr, k].setInitialValue(
                initial_quantities[(i, r, tr, k)]
            )
            """if self.routes[r].start < self.Hmin - self.resolve_margin:
                self.variables["quantity"][(i, r, tr, k)].fixValue() """
        self.print_in_console("Var 'quantity'")

        # Variables : TrailerQuantity
        _capacity = lambda tr: self.instance.get_trailer_property(tr, "Capacity")
        self.trailer_quantity_var = {
            (tr, h): pl.LpVariable(
                f"TrailerQuantity{tr, h}",
                lowBound=0,
                upBound=_capacity(tr),
            )
            for (tr, h) in self.get_var_trailer_quantity_domain()
        }
        self.trailer_quantity_var = SuperDict(self.trailer_quantity_var)
        self.print_in_console("Var 'TrailerQuantity'")

    def create_constraints(self, model, used_routes, artificial_variables):
        # Indices
        ind_td_routes = TupList(self.get_td_routes(used_routes))
        ind_td_routes_r = ind_td_routes.to_dict(result_col=[1, 2])
        ind_customers_hours = self.get_customers_hours()
        _sum_c7_c12_domain = {
            i: self.get_sum_c7_c12_domain(used_routes, i)
            for i in self.instance.get_id_customers()
        }

        # Constraints (1), (2) - Minimize the total cost
        costs = ind_td_routes.to_dict(None).vapply(lambda v: self.cost(*v))
        objective = pl.lpSum(self.route_var * costs)
        if artificial_variables:
            objective += pl.lpSum(2000 * self.artificial_binary_var.values_tl())
        model += objective, "Objective"
        self.print_in_console("Added (Objective) - w/o art. vars.")

        # Constraints : (3) - A shift is only realized by one driver with one driver
        for r, tr_dr in ind_td_routes_r.items():
            model += (
                pl.lpSum(self.route_var[r, tr, dr] for tr, dr in tr_dr) <= 1,
                f"C3_r{r}",
            )
        self.print_in_console("Added (3)")

        # Constraints : (7) - Conservation of the inventory
        for i, h in ind_customers_hours:
            artificial_var = 0
            if artificial_variables:
                artificial_var = self.artificial_quantities_var[i, h]
            model += (
                -self.inventory_var[i, h]
                + self.inventory_var[i, h - 1]
                - pl.lpSum(
                    self.quantity_var[i, r, tr, k]
                    for (r, tr, k) in _sum_c7_c12_domain[i]
                    if self.k_visit_hour[(i, h, r, k)]
                )
                - artificial_var
                - self.instance.get_customer_property(i, "Forecast")[h]
                == 0
            ), f"C7_i{i}_h{h}"

        for i in self.all_customers:
            initial_tank = self.instance.get_customer_property(i, "InitialTankQuantity")
            model += self.inventory_var[i, -1] == initial_tank, f"C7_i{i}_h-1"
        self.print_in_console("Added (7)")

        # Constraints: (A2) - The quantity delivered in an artificial delivery respects quantities constraints
        if artificial_variables:
            for i, h in ind_customers_hours:
                model += (
                    self.artificial_quantities_var[i, h]
                    + self.artificial_binary_var[i, h]
                    * min(
                        self.instance.get_customer_property(i, "Capacity"),
                        self.routes_generator.max_trailer_capacities,
                    )
                    >= 0
                ), f"CA2_i{i}_h{h}"
            self.print_in_console(f"Added (A2)")

        # Constraints : (9) - Conservation of the trailers' inventories
        _sum_c9_domain = self.get_sum_c9_domain(used_routes)
        for tr, h in self.get_c4_c9_domain():
            model += (
                pl.lpSum(
                    self.quantity_var[i, r, tr, k] * self.k_visit_hour[(i, h, r, k)]
                    for (r, i, k) in _sum_c9_domain
                )
                + self.trailer_quantity_var[tr, h - 1]
                == self.trailer_quantity_var[tr, h]
            ), f"C9_tr{tr}_h{h}"

        for tr in self.instance.get_id_trailers():
            initial_quantity = self.instance.get_trailer_property(tr, "InitialQuantity")
            model += (
                self.trailer_quantity_var[tr, -1] == initial_quantity,
                f"C9_tr{tr}_h-1",
            )
        self.print_in_console("Added (9)")

        # Constraints: (15) - Conservation of the total inventory between the beginning of the time horizon and the end
        if self.Hmax >= self.horizon:
            model += (
                pl.lpSum(
                    self.coef_inventory_conservation * self.inventory_var[i, -1]
                    - self.inventory_var[i, self.Hmax - 1]
                    for i in self.instance.get_id_customers()
                )
                <= 0
            ), f"C15"
            self.print_in_console("Added (15)")
        else:
            model += (
                pl.lpSum(
                    self.coef_part_inventory_conservation * self.inventory_var[i, -1]
                    - self.inventory_var[i, self.Hmax - 1]
                    for i in self.instance.get_id_customers()
                )
                <= 0
            ), f"C15"
            self.print_in_console("Added (15)")

        # Constraints: (10) - Quantities delivered don't exceed trailer capacity
        _drivers = self.instance.get_id_drivers()
        for r, i, tr, k in self.get_c10_domain(used_routes):
            _capacity = self.instance.get_customer_property(i, "Capacity")
            model += (
                pl.lpSum(self.route_var[r, tr, dr] * _capacity for dr in _drivers)
                >= -self.quantity_var[i, r, tr, k],
                f"C10_i{i}_r{r}_tr{tr}_k{k}",
            )
        self.print_in_console("Added (10)")

        # Constraints: (11), (12)
        for r, route, i, tr, k in self.get_c11_c12_domain(used_routes):
            # Constraint: (11) - Quantities delivered don't exceed the quantity in the trailer
            visited = lambda j: route.visited[j][0]
            q_tup = lambda j, kp: (visited(j), r, tr, kp)
            hour_tup = lambda j, kp: (
                visited(j),
                self.hour_of_visit[i, r, k],
                r,
                kp,
            )
            visit_tup = lambda j, kp: (r, visited(j), kp, i, k)

            model += (
                pl.lpSum(
                    (
                        self.quantity_var[q_tup(j, kp)]
                        * self.k_visit_hour[hour_tup(j, kp)]
                        * self.visit_before_on_route(*visit_tup(j, kp))
                    )
                    for (j, kp) in self.get_sum_c11_c14_domain(i, r, k)
                )
                + self.quantity_var[i, r, tr, k]
                + self.trailer_quantity_var[(tr, self.hour_of_visit[i, r, k] - 1)]
                >= 0
            ), f"C11_i{i}_r{r}_tr{tr}_k{k}"

            # Constraint: (12) - Quantities delivered don't exceed available space in customer tank
            model += (
                pl.lpSum(
                    (
                        self.quantity_var[i, rp, trp, kp]
                        * self.k_visit_hour[i, self.hour_of_visit[i, r, k], rp, kp]
                        * self.visit_before(i, r, k, rp, kp),
                    )
                    for (rp, trp, kp) in _sum_c7_c12_domain[i]
                    if r != rp and tr != trp
                )
                - self.inventory_var[i, self.hour_of_visit[i, r, k] - 1]
                + self.quantity_var[i, r, tr, k]
                + self.instance.get_customer_property(i, "Capacity")
                >= 0
            ), f"C12_i{i}_r{r}_tr{tr}_k{k}"
        self.print_in_console("Added (11), (12)")

        # Constraints: (13) - Quantities loaded at a source don't exceed trailer capacity
        _drivers = self.instance.get_id_drivers()
        for r, i, tr, k in self.get_c13_domain(used_routes):
            _capacity = self.instance.get_trailer_property(tr, "Capacity")
            model += (
                self.quantity_var[i, r, tr, k]
                <= pl.lpSum(self.route_var[r, tr, dr] for dr in _drivers) * _capacity
            ), f"C13_i{i}_r{r}_tr{tr}_k{k}"
        self.print_in_console("Added (13)")

        # Constraints: (14) - Quantities loaded at a source don't exceed free space in the trailer
        for r, route, i, tr, k in self.get_c14_domain(used_routes):
            visited = lambda j: route.visited[j][0]
            q_tup = lambda j, kp: (visited(j), r, tr, kp)
            hour_tup = lambda j, kp: (
                visited(j),
                self.hour_of_visit[(i, r, k)],
                r,
                kp,
            )
            visit_tup = lambda j, kp: (r, visited(j), kp, i, k)
            model += (
                pl.lpSum(
                    (
                        self.quantity_var[q_tup(j, kp)]
                        * self.k_visit_hour[hour_tup(j, kp)]
                        * self.visit_before_on_route(*visit_tup(j, kp)),
                    )
                    for (j, kp) in self.get_sum_c11_c14_domain(i, r, k)
                )
                + self.quantity_var[i, r, tr, k]
                + self.trailer_quantity_var[(tr, self.hour_of_visit[(i, r, k)] - 1)]
                <= self.instance.get_trailer_property(tr, "Capacity")
            ), f"C14_i{i}_r{r}_tr{tr}_k{k}"
        self.print_in_console("Added (14)")

        # Constraints (4), (5) - Two shifts with same trailer can't happen at the same time
        #   and two shifts realized by the same driver must leave time for the driver to rest between both
        _sum_c4_domain = self.get_sum_c4_domain(used_routes)
        _sum_c5_domain = self.get_sum_c5_domain(used_routes)
        for tr, h in self.get_c4_c9_domain():
            model += (
                pl.lpSum(
                    self.route_var[r, tr, dr]
                    for r, route, dr in _sum_c4_domain
                    if self.runs_at_hour(r, h)
                )
                <= 1,
                f"C4_tr{tr}_h{h}",
            )
        self.print_in_console("Added (4)")

        for dr, h in self.get_c5_domain():
            model += (
                pl.lpSum(
                    self.route_var[r, tr, dr]
                    for r, route, tr in _sum_c5_domain
                    if self.blocks_driver_at_hour(r, dr, h)
                )
                <= 1,
                f"C5_dr{dr}_h{h}",
            )
        self.print_in_console("Added (5)")

        return model

    def select_routes(self, nb=500):
        """
        Selects the indicated number of shifts from self.unused_routes and deletes them from self.unused_routes
        :return: A dictionary whose keys are the indices of the shifts and whose values are instances of RouteLabel
        """
        self.print_in_console(
            "Selecting routes at: ", datetime.now().strftime("%H:%M:%S")
        )
        selected_routes = dict()
        nb = min(nb, len(self.unused_routes))

        for r in list(self.unused_routes.keys())[0:nb]:
            selected_routes[r] = self.unused_routes[r]
            del self.unused_routes[r]
        self.print_in_console(selected_routes)
        return selected_routes

    def get_td_routes(self, used_routes):
        """Returns a list of every possible truple (index_route, index_trailer, index_driver)"""
        return list(
            itertools.product(
                used_routes,
                self.instance.get_id_trailers(),
                self.instance.get_id_drivers(),
            )
        )

    def get_customers_hours(self):
        return list(itertools.product(self.all_customers, range(self.Hmax)))

    def get_var_inventory_domain(self):
        return [
            (i, h) for i in self.all_customers for h in list(range(self.Hmax)) + [-1]
        ]

    def get_var_trailer_quantity_domain(self):
        return [
            (tr, h)
            for tr in self.instance.get_id_trailers()
            for h in list(range(self.Hmax)) + [-1]
        ]

    def get_var_quantity_s_domain(self, used_routes):
        return [
            (r, i, tr, k)
            for r in used_routes
            for i in self.all_sources
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_var_quantity_p_domain(self, used_routes):
        return [
            (r, i, tr, k)
            for r in used_routes
            for i in self.all_customers
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_sum_c4_domain(self, used_routes):
        return [
            (r, route, dr)
            for r, route in used_routes.items()
            for dr in self.instance.get_id_drivers()
        ]

    def get_sum_c5_domain(self, used_routes):
        return [
            (r, route, tr)
            for r, route in used_routes.items()
            for tr in self.instance.get_id_trailers()
        ]

    def get_sum_c9_domain(self, used_routes):
        return [
            (r, i, k)
            for r in used_routes
            for i in self.unique_locations_in[r]
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_sum_c7_c12_domain(self, used_routes, i):
        return [
            (r, tr, k)
            for r in used_routes
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_sum_c11_c14_domain(self, i, r, k):
        return [
            (j, kp)
            for j in range(1, self.k_position(i, r, k))
            for kp in range(1, self.nb_visits[self.routes[r].visited[j][0], r] + 1)
        ]

    def get_c4_c9_domain(self):
        return [
            (tr, h) for tr in self.instance.get_id_trailers() for h in range(self.Hmax)
        ]

    def get_c5_domain(self):
        return [
            (dr, h) for dr in self.instance.get_id_drivers() for h in range(self.Hmax)
        ]

    def get_c10_domain(self, used_routes):
        return [
            (r, i, tr, k)
            for r in used_routes
            for i in self.all_customers
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_c11_c12_domain(self, used_routes):
        return [
            (r, route, i, tr, k)
            for r, route in used_routes.items()
            for i in self.unique_customers_in(route)
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_c13_domain(self, used_routes):
        return [
            (r, i, tr, k)
            for r in used_routes
            for i in self.instance.get_id_sources()
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

    def get_c14_domain(self, used_routes):
        return [
            (r, route, i, tr, k)
            for r, route in used_routes.items()
            for i in self.unique_sources_in(route)
            for tr in self.instance.get_id_trailers()
            for k in range(1, self.nb_visits[i, r] + 1)
        ]

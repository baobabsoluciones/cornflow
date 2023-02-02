from cornflow_client.constants import PYOMO_STOP_MAPPING, PYOMO_STATUS_MAPPING
from pytups import SuperDict
from two_dimension_bin_packing.core import Experiment, Solution
from pyomo.environ import (
    NonNegativeReals,
    Binary,
    NonNegativeIntegers,
    AbstractModel,
    Set,
    Param,
    Var,
    Constraint,
    Objective,
    SolverFactory,
    maximize,
    value,
)


class RightCornerModel(Experiment):
    def __init__(self, instance, solution=None):
        super().__init__(instance, solution)

    def get_pyomo_dict_data(self):
        items = self.instance.get_items()
        item_value = self.instance.get_items_value()
        item_width = self.instance.get_items_width()
        item_height = self.instance.get_items_height()
        bin_width = self.instance.get_bin_width()
        bin_height = self.instance.get_bin_height()
        big_m = self.instance.get_big_m()
        cuts, valid_cuts = self.instance.get_cuts()
        first = self.instance.get_most_value_item()
        second = self.instance.get_second_most_value()

        data = {
            None: {
                "Items": {None: items},
                "ItemValue": item_value,
                "ItemWidth": item_width,
                "ItemHeight": item_height,
                "BinWidth": {None: bin_width},
                "BinHeight": {None: bin_height},
                "BigM": {None: big_m},
                "Cuts": {None: cuts},
                "ValidCuts": valid_cuts,
                "First": {None: first},
                "Second": {None: second},
            }
        }

        return data

    def get_model(self):
        model = AbstractModel()

        # sets
        model.Items = Set()
        model.Cuts = Set()
        model.ValidCuts = Set(model.Cuts)

        # parameters
        model.BinWidth = Param(mutable=True)
        model.BinHeight = Param(mutable=True)
        model.BigM = Param(mutable=True)
        model.ItemWidth = Param(model.Items, mutable=True)
        model.ItemHeight = Param(model.Items, mutable=True)
        model.ItemValue = Param(model.Items, mutable=True)
        model.First = Param(mutable=True)
        model.Second = Param(mutable=True)

        # variables
        model.ItemIn = Var(model.Items, domain=Binary)
        model.XCoordinate = Var(model.Items, domain=NonNegativeIntegers)
        model.YCoordinate = Var(model.Items, domain=NonNegativeIntegers)
        model.FinalItemWidth = Var(model.Items, domain=NonNegativeIntegers)
        model.FinalItemHeight = Var(model.Items, domain=NonNegativeIntegers)
        model.XInterference = Var(model.Items, model.Items, domain=Binary)
        model.YInterference = Var(model.Items, model.Items, domain=Binary)

        # valid cuts
        def valid_cuts(model, cuts):
            return (
                sum(model.ItemIn[item] for item in model.ValidCuts[cuts])
                <= len(model.ValidCuts[cuts]) - 1
            )

        model.valid_cuts = Constraint(model.Cuts, rule=valid_cuts)

        def max_area(model):
            return (
                sum(
                    model.ItemIn[item] * model.ItemWidth[item] * model.ItemHeight[item]
                    for item in model.Items
                )
                <= model.BinWidth * model.BinHeight
            )

        model.max_area = Constraint(rule=max_area)

        def simmetry_a(model):
            return (
                model.XCoordinate[value(model.First)]
                <= model.XCoordinate[value(model.Second)]
            )

        model.simmetry_a = Constraint(rule=simmetry_a)

        def simmetry_b(model):
            return (
                model.YCoordinate[value(model.First)]
                <= model.YCoordinate[value(model.Second)]
            )

        model.simmetry_b = Constraint(rule=simmetry_b)

        # constraints
        def item_in_width(model, item):
            return model.ItemIn[item] <= model.XCoordinate[item]

        model.item_in_width = Constraint(model.Items, rule=item_in_width)

        def item_in_height(model, item):
            return model.ItemIn[item] <= model.YCoordinate[item]

        model.item_in_height = Constraint(model.Items, rule=item_in_height)

        def item_in_bounds_width(model, item):
            return model.XCoordinate[item] - model.FinalItemWidth[item] >= 0

        model.item_in_bounds_width = Constraint(model.Items, rule=item_in_bounds_width)

        def item_in_bounds_height(model, item):
            return model.YCoordinate[item] - model.FinalItemHeight[item] >= 0

        model.item_in_bounds_height = Constraint(
            model.Items, rule=item_in_bounds_height
        )

        def width_limit(model, item):
            return model.XCoordinate[item] <= model.BinWidth

        model.width_limit = Constraint(model.Items, rule=width_limit)

        def height_limit(model, item):
            return model.YCoordinate[item] <= model.BinHeight

        model.height_limit = Constraint(model.Items, rule=height_limit)

        def final_item_width_a(model, item):
            return (
                model.BigM * (model.ItemIn[item] - 1)
                <= model.FinalItemWidth[item] - model.ItemWidth[item]
            )

        model.final_item_width_a = Constraint(model.Items, rule=final_item_width_a)

        def final_item_width_b(model, item):
            return model.FinalItemWidth[item] - model.ItemWidth[item] <= model.BigM * (
                1 - model.ItemIn[item]
            )

        model.final_item_width_b = Constraint(model.Items, rule=final_item_width_b)

        def final_item_height_a(model, item):
            return (
                model.BigM * (model.ItemIn[item] - 1)
                <= model.FinalItemHeight[item] - model.ItemHeight[item]
            )

        model.final_item_height_a = Constraint(model.Items, rule=final_item_height_a)

        def final_item_height_b(model, item):
            return model.FinalItemHeight[item] - model.ItemHeight[
                item
            ] <= model.BigM * (1 - model.ItemIn[item])

        model.final_item_height_b = Constraint(model.Items, rule=final_item_height_b)

        def final_width_domain(model, item):
            return model.FinalItemWidth[item] <= model.BigM * model.ItemIn[item]

        model.final_width_domain = Constraint(model.Items, rule=final_width_domain)

        def final_height_domain(model, item):
            return model.FinalItemHeight[item] <= model.BigM * model.ItemIn[item]

        model.final_height_domain = Constraint(model.Items, rule=final_height_domain)

        def no_width_intercept(model, item_1, item_2):
            if item_1 != item_2:
                return (
                    model.XCoordinate[item_1]
                    + model.FinalItemWidth[item_2]
                    - model.XCoordinate[item_2]
                    <= model.BigM * model.XInterference[item_1, item_2]
                )
            else:
                return Constraint.Skip

        model.no_width_intercept = Constraint(
            model.Items, model.Items, rule=no_width_intercept
        )

        def no_height_intercept(model, item_1, item_2):
            if item_1 != item_2:
                return (
                    model.YCoordinate[item_1]
                    + model.FinalItemHeight[item_2]
                    - model.YCoordinate[item_2]
                    <= model.BigM * model.YInterference[item_1, item_2]
                )
            else:
                return Constraint.Skip

        model.no_height_intercept = Constraint(
            model.Items, model.Items, rule=no_height_intercept
        )

        def no_interference(model, item_1, item_2):
            if item_1 != item_2:
                return (
                    model.XInterference[item_1, item_2]
                    + model.XInterference[item_2, item_1]
                    + model.YInterference[item_1, item_2]
                    + model.YInterference[item_2, item_1]
                    <= 3
                )
            else:
                return Constraint.Skip

        model.no_interference = Constraint(
            model.Items, model.Items, rule=no_interference
        )

        # objective function
        def objective_function(model):
            return sum(
                model.ItemIn[item] * model.ItemValue[item] for item in model.Items
            )

        model.obj = Objective(rule=objective_function, sense=maximize)

        return model

    def solve(self, options):
        data = self.get_pyomo_dict_data()
        model = self.get_model()
        model_instance = model.create_instance(data=data)
        solver_name = options.get("solver", "cbc")
        if "." in solver_name:
            _, solver_name = solver_name.split(".")

        # Setting solver
        if solver_name == "gurobi":
            opt = SolverFactory(solver_name, solver_io="python")
        else:
            opt = SolverFactory(solver_name)
        opt.options.update(options)
        results = opt.solve(model_instance, tee=options.get("msg"))

        if options.get("log"):
            with open("model.log", "w") as of:
                model_instance.pprint(of)

        model.status = results.solver.status
        status = PYOMO_STATUS_MAPPING[model.status]
        status_sol = PYOMO_STOP_MAPPING[results.solver.termination_condition]

        # Check status
        if model.status in ["error", "unknown"]:
            return dict(status=status, status_sol=status_sol)
        elif model.status == "aborted":
            if status_sol != 5:
                return dict(status=status, status_sol=status_sol)
            else:
                pass

        solution_dict = SuperDict()
        solution_dict["included"] = [
            {
                "id": item,
                "x": int(
                    value(model_instance.XCoordinate[item])
                    - value(model_instance.ItemWidth[item])
                ),
                "y": int(
                    value(model_instance.YCoordinate[item])
                    - value(model_instance.ItemHeight[item])
                ),
            }
            for item in model_instance.Items
            if value(model_instance.ItemIn[item]) == 1
        ]

        self.solution = Solution.from_dict(solution_dict)
        # self.plot_solution()

        return dict(status=model.status, status_sol=status_sol)

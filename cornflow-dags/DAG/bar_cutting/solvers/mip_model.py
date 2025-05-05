# Imports from external libraries
from pyomo.environ import (
    AbstractModel,
    Set,
    Param,
    Var,
    Constraint,
    Objective,
    SolverFactory,
    NonNegativeIntegers,
    minimize,
    value,
)

# Imports from cornflow libraries
from cornflow_client.constants import (
    STATUS_TIME_LIMIT,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
    PYOMO_STOP_MAPPING,
)

# Imports from internal modules
from ..core import Experiment, Solution


class MipModel(Experiment):
    def __init__(self, instance, solution=None):
        self.log = ""
        if solution is None:
            solution = Solution(
                {"detail_cutting_patterns": [], "number_cutting_patterns": []}
            )
        super().__init__(instance, solution)
        self.log += "Initialized\n"
        self.data = self.get_pyomo_dict_data()

    def get_pyomo_dict_data(self):
        """Creates the dictionary according to pyomo format"""
        pyomo_instance = {
            "sBars": {None: self.instance.get_bars()},
            "sProducts": {None: self.instance.get_products()},
            "sPatterns": {None: self.instance.get_patterns()},
            "sBars_sPatterns": {None: self.instance.get_bars_patterns()},
            "sBars_sPatterns_sProducts": {
                None: self.instance.get_bars_patterns_products()
            },
            "pBarLength": self.instance.get_bars_length(),
            "pProductLength": self.instance.get_product_length(),
            "pProductDemand": self.instance.get_demand(),
            "pNumberProductsPerBarPattern": self.instance.get_number_products_per_bar_pattern(),
        }
        # print(pyomo_instance)
        return {None: pyomo_instance}

    def get_bar_cutting_model(self):
        """This function builds the bar cutting model"""

        # Create model
        model = AbstractModel()

        # Create sets
        # bars
        model.sBars = Set()
        # products
        model.sProducts = Set()
        # patterns
        model.sPatterns = Set()

        # Create subset
        # this subset represents combinations of bars and patterns
        model.sBars_sPatterns = Set(dimen=2)
        # this subset represents combinations of bars, patterns and products
        model.sBars_sPatterns_sProducts = Set(dimen=3)

        # Create parameters
        # length for each bar
        model.pBarLength = Param(model.sBars, mutable=True)
        # lenght for each product
        model.pProductLength = Param(model.sProducts, mutable=True)
        # demand for each product
        model.pProductDemand = Param(model.sProducts, mutable=True)
        # number of products per bar and pattern
        model.pNumberProductsPerBarPattern = Param(
            model.sBars_sPatterns_sProducts, mutable=True
        )

        # Create variables
        # number of patterns required per bar type
        model.vNumPatternsUsedPerBar = Var(
            model.sBars_sPatterns, domain=NonNegativeIntegers, initialize=0
        )

        # Create constraints
        def c01_demand_satisfaction(model, product):
            """demand satisfaction for each product"""
            return (
                sum(
                    model.pNumberProductsPerBarPattern[bar, pattern, product]
                    * model.vNumPatternsUsedPerBar[bar, pattern]
                    for bar in model.sBars
                    for pattern in model.sPatterns
                    if (bar, pattern, product) in model.sBars_sPatterns_sProducts
                )
                >= model.pProductDemand[product]
            )

        # Create objective function
        def obj_expression(model):
            """minimum total loss of material"""
            return sum(
                model.pBarLength[bar] * model.vNumPatternsUsedPerBar[bar, pattern]
                for bar in model.sBars
                for pattern in model.sPatterns
                if (bar, pattern) in model.sBars_sPatterns
            ) - sum(
                model.pProductLength[product] * model.pProductDemand[product]
                for product in model.sProducts
            )

        # Active constraints
        model.c01_demand_satisfaction = Constraint(
            model.sProducts, rule=c01_demand_satisfaction
        )

        # Add objective function
        model.f_obj = Objective(rule=obj_expression, sense=minimize)

        return model

    def solve(self, config):
        data = self.data
        model = self.get_bar_cutting_model()
        model_instance = model.create_instance(data)

        solver_name = config.get("solver", "cbc")
        if "." in solver_name:
            _, solver_name = solver_name.split(".")

        SOLVER_PARAMETERS = dict(
            time_limit=config.get("timeLimit", 360),
            abs_gap=config.get("abs_gap", 1),
            rel_gap=config.get("rel_gap", 0.01),
            solver=solver_name,
        )
        SOLVER_PARAMETERS = self.get_solver_config(SOLVER_PARAMETERS)

        opt = SolverFactory(solver_name, tee=config.get("msg", 1))
        opt.options.update(SOLVER_PARAMETERS)
        results = opt.solve(model_instance)

        status = results.solver.status
        termination_condition = PYOMO_STOP_MAPPING[results.solver.termination_condition]

        # Check status
        if status in ["error", "unknown", "warning"]:
            self.log += "Infeasible, check data \n"
            return dict(
                status=termination_condition, status_sol=SOLUTION_STATUS_INFEASIBLE
            )
        elif status == "aborted":
            self.log += "Aborted \n"
            if termination_condition != STATUS_TIME_LIMIT:
                return dict(
                    status=termination_condition, status_sol=SOLUTION_STATUS_INFEASIBLE
                )

        solution_dict = dict()
        solution_dict["detail_cutting_patterns"] = [
            dict(
                id_bar=ba,
                id_pattern=pa,
                id_product=pr,
                number_of_products=int(
                    value(model_instance.pNumberProductsPerBarPattern[ba, pa, pr])
                ),
            )
            for (
                ba,
                pa,
                pr,
            ) in model_instance.sBars_sPatterns_sProducts
            if value(model_instance.vNumPatternsUsedPerBar[ba, pa]) > 0
        ]
        solution_dict["number_cutting_patterns"] = [
            dict(
                id_bar=ba,
                id_pattern=pa,
                number_of_patterns=int(
                    value(model_instance.vNumPatternsUsedPerBar[ba, pa])
                ),
            )
            for (
                ba,
                pa,
            ) in model_instance.sBars_sPatterns
            if value(model_instance.vNumPatternsUsedPerBar[ba, pa]) > 0
        ]
        # print(solution_dict)

        self.solution = Solution.from_dict(solution_dict)

        self.log += "Solving complete\n"

        return dict(
            status=termination_condition,
            status_sol=SOLUTION_STATUS_FEASIBLE,
        )

# Imports from external libraries
import re
from pyomo.environ import (
    AbstractModel,
    Set,
    Param,
    Var,
    Constraint,
    Objective,
    SolverFactory,
    Binary,
    NonNegativeIntegers,
    NonNegativeReals,
    minimize,
    maximize,
    value,
    Suffix,
)

# Imports from cornflow libraries
from cornflow_client.constants import (
    STATUS_NOT_SOLVED,
    STATUS_OPTIMAL,
    STATUS_INFEASIBLE,
    STATUS_UNBOUNDED,
    STATUS_UNDEFINED,
    STATUS_TIME_LIMIT,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
)

# Imports from internal modules
from ..core import Experiment, Solution


pyomo_stop_mapping = dict(
    unbounded=STATUS_UNBOUNDED,
    infeasible=STATUS_INFEASIBLE,
    invalidProblem=STATUS_NOT_SOLVED,
    solverFailure=STATUS_NOT_SOLVED,
    internalSolverError=STATUS_NOT_SOLVED,
    error=STATUS_NOT_SOLVED,
    userInterrupt=STATUS_NOT_SOLVED,
    resourceInterrupt=STATUS_NOT_SOLVED,
    licensingProblem=STATUS_NOT_SOLVED,
    maxTimeLimit=STATUS_TIME_LIMIT,
    maxIterations=STATUS_TIME_LIMIT,
    maxEvaluations=STATUS_TIME_LIMIT,
    globallyOptimal=STATUS_OPTIMAL,
    locallyOptimal=STATUS_OPTIMAL,
    optimal=STATUS_OPTIMAL,
    minFunctionValue=STATUS_UNDEFINED,
    minStepLength=STATUS_UNDEFINED,
    other=STATUS_UNDEFINED,
)
pyomo_status_mapping = dict(
    ok=SOLUTION_STATUS_FEASIBLE,
    warning=SOLUTION_STATUS_FEASIBLE,
    error=SOLUTION_STATUS_INFEASIBLE,
    aborted=SOLUTION_STATUS_INFEASIBLE,
    unknown=SOLUTION_STATUS_INFEASIBLE,
)


class ColumnGeneration(Experiment):
    def __init__(self, instance, solution=None):
        self.log = ""
        if solution is None:
            solution = Solution(
                {"detail_cutting_patterns": [], "number_cutting_patterns": []}
            )
        super().__init__(instance, solution)
        self.log += "Initialized\n"
        self.data_master_problem = self.get_pyomo_dict_data_master_problem()
        self.data_subproblem = self.get_pyomo_dict_data_subproblem()
        self.pLengthBar1 = self.instance.get_bar1_length()
        self.pLengthBar2 = self.instance.get_bar2_length()

    def get_pyomo_dict_data_master_problem(self):
        """Creates the dictionary for the master problem according to pyomo format"""
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
        return {None: pyomo_instance}

    def get_pyomo_dict_data_subproblem(self):
        """Creates the dictionary for the subproblems according to pyomo format"""
        pyomo_instance = {
            "sProducts": {None: self.instance.get_products()},
            "pProductLength": self.instance.get_product_length(),
        }
        return {None: pyomo_instance}

    def get_master_problem(self, relax=True):
        """This function builds the master/original problem (master problem if relax=True, original proble if relax=False)"""

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
        # this subset represents feasible combinations of bars and patterns
        model.sBars_sPatterns = Set(dimen=2)
        # this subset represents feasible combinations of bars, patterns and products
        model.sBars_sPatterns_sProducts = Set(dimen=3)

        # Create parameters
        # length for each bar
        model.pBarLength = Param(model.sBars, mutable=True)
        # length for each product
        model.pProductLength = Param(model.sProducts, mutable=True)
        # demand for each product
        model.pProductDemand = Param(model.sProducts, mutable=True)
        # number of products per bar and pattern
        model.pNumberProductsPerBarPattern = Param(
            model.sBars_sPatterns_sProducts, mutable=True
        )

        # Create variables
        # domain depending on the problem (master or original)
        if relax:
            vartype = NonNegativeReals
        else:
            vartype = NonNegativeIntegers

        # number of patterns required per bar type
        model.vNumPatternsUsedPerBar = Var(
            model.sBars_sPatterns, domain=vartype, initialize=0
        )

        # Create constraints
        def c01_demand_satisfaction(model, iProduct):
            """demand satisfaction for each product"""
            return (
                sum(
                    model.pNumberProductsPerBarPattern[iBar, iPattern, iProduct]
                    * model.vNumPatternsUsedPerBar[iBar, iPattern]
                    for iBar in model.sBars
                    for iPattern in model.sPatterns
                    if (iBar, iPattern, iProduct) in model.sBars_sPatterns_sProducts
                )
                >= model.pProductDemand[iProduct]
            )

        # Create objective function
        def obj_expression(model):
            """minimum total loss of material"""
            return sum(
                model.pBarLength[iBar] * model.vNumPatternsUsedPerBar[iBar, iPattern]
                for iBar in model.sBars
                for iPattern in model.sPatterns
                if (iBar, iPattern) in model.sBars_sPatterns
            ) - sum(
                model.pProductLength[iProduct] * model.pProductDemand[iProduct]
                for iProduct in model.sProducts
            )

        # Active constraints
        model.c01_demand_satisfaction = Constraint(
            model.sProducts, rule=c01_demand_satisfaction
        )

        # Add objective function
        model.f_obj = Objective(rule=obj_expression, sense=minimize)

        return model

    def get_subproblem(self, pBarXLength, pDuals):
        """This function builds the subproblem (knapsack problem)"""

        # Create model
        model = AbstractModel()

        # Create sets
        # products
        model.sProducts = Set()

        # Create parameters
        # length for each product
        model.pProductLength = Param(model.sProducts, mutable=True)

        # Create variables
        # number of products per bar
        model.vNumberProductsPerBar = Var(
            model.sProducts, domain=NonNegativeIntegers, initialize=0
        )

        # Create constraints
        def c01_bar_length_satisfaction(model):
            """bar length satisfaction"""
            return (
                sum(
                    model.pProductLength[iProduct]
                    * model.vNumberProductsPerBar[iProduct]
                    for iProduct in model.sProducts
                )
                <= pBarXLength
            )

        # Create objective function
        def obj_expression(model):
            """maximize the value of the pieces that will be part of a new pattern"""
            return sum(
                pDuals[iProduct] * model.vNumberProductsPerBar[iProduct]
                for iProduct in model.sProducts
            )

        # Active constraints
        model.c01_bar_length_satisfaction = Constraint(rule=c01_bar_length_satisfaction)

        # Add objective function
        model.f_obj = Objective(rule=obj_expression, sense=maximize)

        return model

    def solve(self, config):

        solver_name = config.get("solver", "cbc")
        if "." in solver_name:
            _, solver_name = solver_name.split(".")

        SOLVER_PARAMETERS = dict(
            sec=config.get("timeLimit", 360),
            allow=config.get("gapAbs", 1),
            ratio=config.get("gaPRel", 0.01),
            tee=config.get("msg", 1),
        )

        opt = SolverFactory(solver_name)
        opt.options.update(SOLVER_PARAMETERS)

        more_patterns_bar1 = True
        more_patterns_bar2 = True

        while more_patterns_bar1 or more_patterns_bar2:
            # Solve the master problem as a relaxed LP and get the dual prices
            data_master_problem = self.data_master_problem
            model_master_problem = self.get_master_problem(relax=True)
            model_instance_master_problem = model_master_problem.create_instance(
                data_master_problem
            )
            model_instance_master_problem.dual = Suffix(direction=Suffix.IMPORT_EXPORT)

            opt.solve(model_instance_master_problem)

            duals = {}
            for c in model_instance_master_problem.component_objects(
                Constraint, active=True
            ):
                for index in c:
                    duals[index] = model_instance_master_problem.dual[c[index]]

            if more_patterns_bar1:
                # Solve the subproblem to find a new pattern for the bar1
                data_subproblem1 = self.data_subproblem
                model_subproblem1 = self.get_subproblem(self.pLengthBar1, duals)
                model_instance_subproblem1 = model_subproblem1.create_instance(
                    data_subproblem1
                )

                opt.solve(model_instance_subproblem1)

                if model_instance_subproblem1.f_obj() > self.pLengthBar1:
                    # Add the new pattern to the data problem
                    # New pattern name
                    last_pattern_name = data_master_problem[None]["sPatterns"][
                        None
                    ].sorted()[-1]
                    name_format = re.compile("([a-z]+)([0-9]+)")
                    matcher = name_format.search(last_pattern_name)
                    new_pattern_name = matcher.group(1) + str(int(matcher.group(2)) + 1)
                    # Add the new pattern to 'sPatterns'
                    data_master_problem[None]["sPatterns"][None].append(
                        new_pattern_name
                    )
                    # Add the new pattern to 'sBars_sPatterns'
                    data_master_problem[None]["sBars_sPatterns"][None].append(
                        (self.instance.get_bar1_id(), new_pattern_name)
                    )
                    # Add the new pattern to 'sBars_sPatterns_sProducts'
                    for iProduct in data_subproblem1[None]["sProducts"][None]:
                        data_master_problem[None]["sBars_sPatterns_sProducts"][
                            None
                        ].append(
                            (self.instance.get_bar1_id(), new_pattern_name, iProduct)
                        )
                    # Add the new pattern to 'pNumberProductsPerBarPattern'
                    for iProduct in data_subproblem1[None]["sProducts"][None]:
                        data_master_problem[None]["pNumberProductsPerBarPattern"][
                            self.instance.get_bar1_id(), new_pattern_name, iProduct
                        ] = value(
                            model_instance_subproblem1.vNumberProductsPerBar[iProduct]
                        )
                else:
                    # Stop the search
                    more_patterns_bar1 = False

            if more_patterns_bar2:
                # Solve the subproblem to find a new pattern for the bar2
                data_subproblem2 = self.data_subproblem
                model_subproblem2 = self.get_subproblem(self.pLengthBar2, duals)
                model_instance_subproblem2 = model_subproblem2.create_instance(
                    data_subproblem2
                )

                opt.solve(model_instance_subproblem2)

                if model_instance_subproblem2.f_obj() > self.pLengthBar2:
                    # Add the new pattern to the data problem
                    # New pattern name
                    last_pattern_name = data_master_problem[None]["sPatterns"][
                        None
                    ].sorted()[-1]
                    name_format = re.compile("([a-z]+)([0-9]+)")
                    matcher = name_format.search(last_pattern_name)
                    new_pattern_name = matcher.group(1) + str(int(matcher.group(2)) + 1)
                    # Add the new pattern to 'sPatterns'
                    data_master_problem[None]["sPatterns"][None].append(
                        new_pattern_name
                    )
                    # Add the new pattern to 'sBars_sPatterns'
                    data_master_problem[None]["sBars_sPatterns"][None].append(
                        (self.instance.get_bar2_id(), new_pattern_name)
                    )
                    # Add the new pattern to 'sBars_sPatterns_sProducts'
                    for iProduct in data_subproblem2[None]["sProducts"][None]:
                        data_master_problem[None]["sBars_sPatterns_sProducts"][
                            None
                        ].append(
                            (self.instance.get_bar2_id(), new_pattern_name, iProduct)
                        )
                    # Add the new pattern to 'pNumberProductsPerBarPattern'
                    for iProduct in data_subproblem2[None]["sProducts"][None]:
                        data_master_problem[None]["pNumberProductsPerBarPattern"][
                            self.instance.get_bar2_id(), new_pattern_name, iProduct
                        ] = value(
                            model_instance_subproblem2.vNumberProductsPerBar[iProduct]
                        )
                else:
                    # Stop the search
                    more_patterns_bar2 = False

        # Solve the original problem as a non-relaxed LP
        data_original_problem = self.data_master_problem
        model_original_problem = self.get_master_problem(relax=False)
        model_instance_original_problem = model_original_problem.create_instance(
            data_original_problem
        )

        results = opt.solve(model_instance_original_problem)

        status = pyomo_status_mapping[results.solver.status]
        status_sol = pyomo_stop_mapping[results.solver.termination_condition]

        # Check status
        if status == SOLUTION_STATUS_INFEASIBLE:
            self.log += "Infeasible, check data \n"
            return dict(status=status, status_sol=status_sol)

        solution_dict = dict()
        solution_dict["detail_cutting_patterns"] = [
            dict(
                id_bar=ba,
                id_pattern=pa,
                id_product=pr,
                number_of_products=value(
                    model_instance_original_problem.pNumberProductsPerBarPattern[
                        ba, pa, pr
                    ]
                ),
            )
            for (
                ba,
                pa,
                pr,
            ) in model_instance_original_problem.sBars_sPatterns_sProducts
            if value(model_instance_original_problem.vNumPatternsUsedPerBar[ba, pa]) > 0
        ]
        solution_dict["number_cutting_patterns"] = [
            dict(
                id_bar=ba,
                id_pattern=pa,
                number_of_patterns=value(
                    model_instance_original_problem.vNumPatternsUsedPerBar[ba, pa]
                ),
            )
            for (
                ba,
                pa,
            ) in model_instance_original_problem.sBars_sPatterns
            if value(model_instance_original_problem.vNumPatternsUsedPerBar[ba, pa]) > 0
        ]
        # print(solution_dict)

        self.solution = Solution.from_dict(solution_dict)

        self.log += "Solving complete\n"

        return dict(
            status=status,
            status_sol=status_sol,
        )

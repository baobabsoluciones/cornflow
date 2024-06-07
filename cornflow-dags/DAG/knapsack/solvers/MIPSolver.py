from ..core import Experiment, Solution
from pyomo.environ import (
    AbstractModel,
    Set,
    Param,
    Var,
    summation,
    Constraint,
    Objective,
    SolverFactory,
    Binary,
    maximize,
    value,
)
from cornflow_client.constants import (
    STATUS_TIME_LIMIT,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
    PYOMO_STOP_MAPPING
)


class MIPSolver(Experiment):
    def __init__(self, instance, solution=None):
        self.log = ""
        if solution is None:
            solution = Solution({"include": []})
        super().__init__(instance, solution)
        self.log += "Initialized\n"

    def get_pyomo_dict_data(self):
        """Creates the dictionary according to pyomo format"""
        id_objects = self.instance.data["ids"]
        pyomo_instance = {
            "sObjects": {None: id_objects},
            "pValue": self.instance.get_objects_values(),
            "pWeight": self.instance.get_objects_weights(),
            "pWeightCapacity": {None: self.instance.get_weight_capacity()},
        }
        return {None: pyomo_instance}

    def get_knapsack_model(self):
        """Builds the model"""
        model = AbstractModel()
        # Sets
        model.sObjects = Set()
        # Parameters
        model.pValue = Param(model.sObjects, mutable=True)
        model.pWeight = Param(model.sObjects, mutable=True)
        model.pWeightCapacity = Param(mutable=True)
        # Variables
        model.v01Include = Var(model.sObjects, domain=Binary)

        # Create constraints
        def c1_weight_capacity(model):
            return (
                sum(model.pWeight[i] * model.v01Include[i] for i in model.sObjects)
                <= model.pWeightCapacity
            )

        # Objective function
        def obj_expression(model):
            return summation(model.pValue, model.v01Include)

        # Add constraints
        model.c1_weight_capacity = Constraint(rule=c1_weight_capacity)
        # Add objetive function
        model.obj_function = Objective(rule=obj_expression, sense=maximize)

        return model

    def solve(self, config):
        data = self.get_pyomo_dict_data()
        model = self.get_knapsack_model()
        model_instance = model.create_instance(data)

        solver_name = config.get("solver","cbc")
        if "." in solver_name:
            _, solver_name = solver_name.split(".")

        opt = SolverFactory(solver_name)
        opt.options.update(self.get_solver_config(config))
        results = opt.solve(model_instance, tee=config.get("msg", True))

        status = results.solver.status
        termination_condition = PYOMO_STOP_MAPPING[results.solver.termination_condition]

        # Check status
        if status in ["error", "unknown", "warning"]:
            self.log += "Infeasible, check data \n"
            return dict(
                status=termination_condition,
                status_sol=SOLUTION_STATUS_INFEASIBLE
            )
        elif status == "aborted":
            self.log += "Aborted \n"
            if termination_condition != STATUS_TIME_LIMIT:
                return dict(
                    status=termination_condition,
                    status_sol=SOLUTION_STATUS_INFEASIBLE
                )

        self.solution.data["include"] = [
            {"id": i}
            for i in model_instance.sObjects
            if value(model_instance.v01Include[i]) == 1
        ]
        self.log += "Solving complete\n"

        return dict(
            status=termination_condition,
            status_sol=SOLUTION_STATUS_FEASIBLE
        )

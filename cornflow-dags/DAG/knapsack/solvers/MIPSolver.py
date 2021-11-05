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
    STATUS_NOT_SOLVED,
    STATUS_OPTIMAL,
    STATUS_INFEASIBLE,
    STATUS_UNBOUNDED,
    STATUS_UNDEFINED,
    STATUS_TIME_LIMIT,
)

pyomo_status_mapping = dict(
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

        solver_name = config.get("solver", "cbc")
        if "." in solver_name:
            _, solver_name = solver_name.split(".")

        opt = SolverFactory(solver_name)
        opt.options.update(config)
        results = opt.solve(model_instance)
        model.status = results.solver.status
        status_sol = pyomo_status_mapping[results.solver.termination_condition]

        # Check status
        if model.status not in ["ok", "warning"]:
            return dict(status=model.status, status_sol=status_sol)

        self.solution.data["include"] = [
            {"id": i}
            for i in model_instance.sObjects
            if value(model_instance.v01Include[i]) == 1
        ]
        self.log += "Solving complete\n"

        return dict(status=model.status, status_sol=status_sol)

"""
Base code for the application core.
"""

# Partial imports
from abc import ABC, abstractmethod
from timeit import default_timer as timer
from typing import Type, Dict, List, Tuple, Union

from jsonschema import Draft7Validator
from pytups import SuperDict

from cornflow_client.constants import (
    STATUS_CONV,
    STATUS_OPTIMAL,
    STATUS_INFEASIBLE,
    SOLUTION_STATUS_FEASIBLE,
    SOLUTION_STATUS_INFEASIBLE,
    NoSolverException,
    BadConfiguration,
    BadSolution,
    BadInstance,
)
from .experiment import ExperimentCore

# Imports from internal modules
from .instance import InstanceCore
from .solution import SolutionCore


class ApplicationCore(ABC):
    """
    The application template.
    """

    # We create a new attribute controlling the use of the notification mail function
    def __init__(self):
        self._notify = False

    @property
    def notify(self) -> bool:
        return self._notify

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Mandatory property

        :return: the name of the class.
        """
        raise NotImplementedError()

    @property
    def description(self) -> Union[str, None]:
        """
        Optional property

        :return: the description of the class
        """
        return None

    @property
    def default_args(self) -> Union[Dict, None]:
        """
        Optional property

        :return: the default args for the DAG
        """
        return None

    @property
    def extra_args(self) -> Union[Dict, None]:
        """
        Optional property

        :return: dictionary with optional arguments for the DAG
        """
        return None

    @property
    @abstractmethod
    def instance(self) -> Type[InstanceCore]:
        """
        Mandatory property

        :return: the constructor for the instance.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def solution(self) -> Type[SolutionCore]:
        """
        Mandatory property

        :return: the constructor for the solution.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def schema(self) -> dict:
        """
        Mandatory property

        :return: the configuration schema used for the solve() method.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def test_cases(
        self,
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Mandatory property

        :return: a list of datasets following the json-schema.
          if each element in the list is:

          * **dict**: each element is an instance
          * **tuple**: the first part is the instance, the second its solution

          it can also return a list of dicts, where the keys are:

          * **name**: name of the test case.
          * **description** optional field with a description of the test case.
          * **instance**: the instance data.
          * **solution**: the solution data (optional)
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def solvers(self) -> Dict[str, Type[ExperimentCore]]:
        """
        Mandatory property

        :return: a dictionary of constructors for solution methods for this particular problem.
        """
        raise NotImplementedError()

    def _validate_config(self, config):
        """Validates the configuration dictionary against the schema."""
        validator = Draft7Validator(self.schema)
        if not validator.is_valid(config):
            error_list = [str(e) for e in validator.iter_errors(config)]
            raise BadConfiguration(
                f"The configuration does not match the schema:\n{error_list}"
            )

    def _prepare_instance_and_solution(self, data, solution_data=None):
        """Creates and validates instance and optional solution objects."""
        inst = self.instance.from_dict(data)
        inst_errors = inst.check_schema()
        if inst_errors:
            raise BadInstance(f"The instance does not match the schema:\n{inst_errors}")

        sol = None
        if solution_data is not None:
            sol = self.solution.from_dict(solution_data)
            sol_errors = sol.check_schema()
            if sol_errors:
                raise BadSolution(
                    f"The solution does not match the schema:\n{sol_errors}"
                )
        return inst, sol

    def _check_instance_errors(self, inst):
        """Performs instance data checks and identifies critical errors."""
        instance_checks = SuperDict(inst.data_checks())
        warnings_tables = (
            SuperDict.from_dict(inst.schema_checks)["properties"]
            .vfilter(lambda v: v.get("is_warning", False))
            .keys()
        )
        instance_errors = instance_checks.kfilter(lambda k: k not in warnings_tables)

        has_errors = False
        for error_table in instance_errors.values():
            # Check if the error table/value indicates an error
            if isinstance(error_table, (list, dict)) and len(error_table) > 0:
                has_errors = True
                break
            # Check for non-empty scalar values considered errors
            elif error_table and not isinstance(error_table, (list, dict)):
                has_errors = True
                break

        return instance_checks, has_errors

    def _execute_solver(self, inst, sol, config):
        """Instantiates and runs the solver, returning output and timing."""
        solver_name = config.get("solver", self.get_default_solver_name())
        solver_class = self.get_solver(name=solver_name)
        if solver_class is None:
            # This check might be redundant if config validation includes solver names
            raise NoSolverException(f"Solver {solver_name} is not available")

        algo = solver_class(inst, sol)
        start = timer()
        output = algo.solve(config)
        elapsed_time = timer() - start

        # Ensure output is a dict for consistency
        if isinstance(output, int):
            output = dict(status=output)

        return algo, output, solver_name, elapsed_time

    def _build_base_log_json(self, output, solver_name, elapsed_time):
        """Builds the initial log_json dictionary."""
        status = output.get("status")
        return {
            **output,
            "time": elapsed_time,
            "solver": solver_name,
            "status": STATUS_CONV.get(status, "Unknown"),
            "status_code": status,
            "sol_code": SOLUTION_STATUS_INFEASIBLE,  # Default to infeasible
        }

    def _determine_final_solution_code(self, algo, status_sol):
        """Determines the final solution status code."""
        if status_sol is not None:
            return status_sol
        elif algo.solution is not None and algo.solution.data:
            return SOLUTION_STATUS_FEASIBLE
        else:
            # Return default infeasible if no explicit status or valid solution found
            return SOLUTION_STATUS_INFEASIBLE

    def _get_log_text(self, algo):
        """Safely retrieves the log text from the algorithm object."""
        try:
            return algo.log
        except AttributeError:
            return ""  # Solver might not have a .log attribute

    def _validate_and_check_solution(self, algo):
        """
        Validates the solution schema and performs data checks if available.
        Returns the solution dict and checks dict, or (None, None).
        Raises BadSolution if schema validation fails.
        """
        if algo.solution is None:
            # This case should ideally be prevented by checking sol_code before calling,
            # but added as a safeguard.
            raise BadSolution(
                "Attempted to validate solution, but algo.solution is None."
            )

        # Check solution schema
        sol_schema_errors = algo.solution.check_schema()
        if sol_schema_errors:
            raise BadSolution(
                f"The final solution does not match the schema:\n{sol_schema_errors}"
            )

        final_sol_dict = algo.solution.to_dict()
        solution_checks = None

        # Perform data checks only if a valid solution dict was obtained
        # and the solver implements data_checks
        if final_sol_dict:  # Checks for non-None and non-empty dict
            try:
                solution_checks = algo.data_checks()
            except AttributeError:
                # Solver doesn't implement data_checks, which is acceptable.
                solution_checks = None

        return final_sol_dict, solution_checks

    def _format_log_and_solution(self, algo, output, solver_name, elapsed_time):
        """Formats logs, validates and checks the solution."""

        # 1. Build initial log dictionary
        log_json = self._build_base_log_json(output, solver_name, elapsed_time)

        # 2. Determine final solution status code and update log
        status_sol = output.get("status_sol")
        final_sol_code = self._determine_final_solution_code(algo, status_sol)
        log_json["sol_code"] = final_sol_code

        # 3. Get text log
        log_txt = self._get_log_text(algo)

        # 4. Validate and check solution if feasible/optimal
        final_sol_dict = None
        solution_checks = None
        if final_sol_code > 0:
            # Raises BadSolution if schema validation fails
            final_sol_dict, solution_checks = self._validate_and_check_solution(algo)

        return final_sol_dict, solution_checks, log_txt, log_json

    def solve(
        self, data: dict, config: dict, solution_data: dict = None
    ) -> Tuple[Dict, Union[Dict, None], Union[Dict, None], str, Dict]:
        """
        Solves the problem instance using the specified configuration.

        :param data: Dictionary representing the problem instance.
        :param config: Dictionary containing execution configuration.
        :param solution_data: Optional dictionary with an initial solution.
        :return: Tuple containing (solution, solution_checks, instance_checks, log_txt, log_json).
        """
        if config.get("msg", True):
            print("Solving the model")

        # 1. Validate configuration
        self._validate_config(config)

        # 2. Prepare instance and potential initial solution
        inst, sol_initial = self._prepare_instance_and_solution(data, solution_data)

        # 3. Check instance for critical errors
        instance_checks, has_errors = self._check_instance_errors(inst)

        if has_errors:
            # Return early if instance has critical errors
            solver_name = config.get("solver", self.get_default_solver_name())
            log_json = dict(
                time=0,
                solver=solver_name,
                status="Infeasible",
                status_code=STATUS_INFEASIBLE,
                sol_code=SOLUTION_STATUS_INFEASIBLE,
            )
            # Ensure solution dict is empty, not None, consistent with successful returns
            return dict(), None, instance_checks, "", log_json

        # 4. Execute solver
        algo, output, solver_name, elapsed_time = self._execute_solver(
            inst, sol_initial, config
        )

        # 5. Format log and process solution
        sol_final, solution_checks, log_txt, log_json = self._format_log_and_solution(
            algo, output, solver_name, elapsed_time
        )

        # Ensure solution is an empty dict if None for type consistency
        if sol_final is None:
            sol_final = dict()

        return sol_final, solution_checks, instance_checks, log_txt, log_json

    def check(
        self, instance_data: dict, solution_data: dict = None
    ) -> Tuple[Dict, Dict, Dict]:
        """
        Checks the instance and solution data
        :param instance_data: json data of the instance
        :param solution_data: json data of the solution
        :return: instance checks, solution checks, log
        """
        solver = self.get_default_solver_name()
        solver_class = self.get_solver(name=solver)
        if solver_class is None:
            raise NoSolverException("No solver is available")
        inst = self.instance.from_dict(instance_data)

        instance_checks = inst.data_checks()

        if solution_data is not None:
            sol = self.solution.from_dict(solution_data)
            algo = solver_class(inst, sol)
            start = timer()
            solution_checks = algo.data_checks()
        else:
            start = timer()
            solution_checks = None

        log = dict(
            time=timer() - start,
            solver=solver,
            status="Optimal",
            status_code=STATUS_OPTIMAL,
            sol_code=SOLUTION_STATUS_FEASIBLE,
        )

        return instance_checks, solution_checks, log

    def get_solver(self, name: str = "default") -> Union[Type[ExperimentCore], None]:
        """
        :param name: name of the solver to find

        :return: the constructor for a solver matching the name
        """
        if "." in name:
            solver = name.split(".")[0]
        else:
            solver = name
        return self.solvers.get(solver)

    def get_default_solver_name(self) -> str:
        """
        :return: the name of the default solver
        """
        return self.schema["properties"]["solver"]["default"]

    def get_schemas(self) -> Dict[str, Dict]:
        """
        :return: a dictionary with the three schemas that define the solution method
        """
        return dict(
            instance=self.instance.schema,
            solution=self.solution.schema,
            config=self.schema,
            instance_checks=self.instance.schema_checks,
            solution_checks=list(self.solvers.values())[0].schema_checks,
        )

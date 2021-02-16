from hackathonbaobab2020.solvers import get_solver
from hackathonbaobab2020.core import Instance
from hackathonbaobab2020.core.tools import dict_to_list
from timeit import default_timer as timer
from utils import cf_solve, get_arg

"""
Functions
"""

def solve_from_dict(data, solver="default", options= {}):
    """
    :param data: json for the problem
    :param solver: solver to use
    :param options: options
    :return: solution and log
    """
    print("Solving the model")
    print(solver)
    solver_class = get_solver(name = solver)
    print(data)
    inst = Instance.from_dict(data)
    algo = solver_class(inst)
    start = timer()
    
    try:
        status = algo.solve(options)
        print("ok")
    except Exception as e:
        print("problem was not solved")
        print(e)
        status = 0
    
    if status != 0:
        # export everything:
        status_conv = {4: "Optimal", 2: "Feasible", 3: "Infeasible", 0: "Unknown"}
        log = dict(time=timer() - start, solver=solver, status=status_conv.get(status, "Unknown"))
        sol = dict_to_list(algo.solution.data, 'job')
    else:
        log = "error"
        sol = {}
    # TODO: change that log
    log = log["status"]
    return sol, log

def solve_hk(**kwargs):
    return cf_solve(solve_from_dict, "hk_solution_schema", **kwargs)


def test_hk(**kwargs):
    print("This function should only be used for tests when reaching airflow directly")
    data = get_arg("data", kwargs)
    print(data)
    solver_name = get_arg("solver", kwargs)
    options = get_arg("options", kwargs)

    return solve_from_dict(data, solver_name, options)


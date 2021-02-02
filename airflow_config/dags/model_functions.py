import pulp as pl
import orloge as ol
import os


"""
Functions
"""

def solve_model(data, config):
    """
    :param data: pulp json for the model
    :param config: pulp config for solver
    :return:
    """
    print("Solving the model")
    var, model = pl.LpProblem.from_dict(data)

    # we overwrite the logPath argument before solving.
    log_path = config['logPath'] = 'temp.log'
    config['msg'] = 0
    solver = pl.get_solver_from_dict(config)
    if not solver.available():
        raise NoSolverException()
    model.solve(solver)
    solution = model.to_dict()

    print("Model solved")
    with open(log_path, "r") as f:
        log = f.read()

    # we convert the log into orloge json
    equivs = \
        dict(
            CPLEX_CMD='CPLEX', CPLEX_PY='CPLEX', CPLEX_DLL='CPLEX',
            GUROBI='GUROBI', GUROBI_CMD='GUROBI',
            PULP_CBC_CMD='CBC', COIN_CMD='CBC'
        )
    solver_name = equivs.get(solver.name)
    log_dict = None
    if solver_name:
        try:
            log_dict = ol.get_info_solver(path=log, solver=solver_name, get_progress=True, content=True)
        except:
            log_dict = dict()
        else:
            log_dict['progress'] = log_dict['progress'].fillna('').to_dict(orient='list')
            # TODO: there is a problem with string quotes that brings problems when reading this json
            #  from the database
    print("Log read")

    try:
        os.remove(log_path)
    except:
        pass

    return solution, log, log_dict


class NoSolverException(Exception):
    pass
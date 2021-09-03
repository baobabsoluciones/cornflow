import os
from solvers import get_cbc

# list of available solvers
    # * HiGHS: https://www.maths.ed.ac.uk/hall/HiGHS/
    # * CBC: https://projects.coin-or.org/Cbc
    # * SCIP: https://www.scipopt.org/
    # * CHOCO: https://github.com/chocoteam/choco-solver
    # * MIPCL: https://github.com/onebitbrain/MIPCL/blob/master/bin/mps_mipcl
    # * glpk: https://www.gnu.org/software/glpk/
available_solver = ['HiGHS','CBC','SCIP','CHOCO','MIPCL','glpk']

# list of solvers that will be installed
solver_list = os.getenv('SOLVER_LIST','CBC').split(',')

def install(s):
    if s in 'CBC':
        get_cbc.install()

for solver in solver_list:

    if (solver in available_solver):
        install(solver)

    else:
        print(solver+' is not in cornflow available solver list')
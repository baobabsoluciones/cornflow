import os
from solvers import get_cbc, get_glpk, get_highs, get_choco, get_mipcl, get_gurobi

# list of available solvers
# * HiGHS: https://www.maths.ed.ac.uk/hall/HiGHS/
# * CBC: https://projects.coin-or.org/Cbc
# * CHOCO: https://github.com/chocoteam/choco-solver
# * MIPCL: https://github.com/onebitbrain/MIPCL/blob/master/bin/mps_mipcl
# * glpk: https://www.gnu.org/software/glpk/
# * Gurobi optimizer: https://www.gurobi.com/
available_solver = ["HiGHS", "CBC", "CHOCO", "MIPCL", "glpk", "gurobi"]

# list of solvers that will be installed
solver_list = os.getenv("SOLVER_LIST", "CBC,glpk,HiGHS,CHOCO,MIPCL,gurobi").split(",")


def install(s):
    if s in "CBC":
        get_cbc.install()
    if s in "glpk":
        get_glpk.install()
    if s in "HiGHS":
        get_highs.install()
    if s in "CHOCO":
        get_choco.install()
    if s in "MIPCL":
        get_mipcl.install()
    if s in "gurobi":
        get_gurobi.install()


for solver in solver_list:

    if solver in available_solver:
        install(solver)

    else:
        print(solver + " is not in cornflow available solver list")

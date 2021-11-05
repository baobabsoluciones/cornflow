from logging import error
import subprocess
import git
import os
import pwd
import grp


def install():

    #####  HiGHS - high performance software for linear optimization ##########
    # Open source serial and parallel solvers for large-scale
    # sparse linear programming (LP) and
    # mixed-integer programming (MIP) models
    # More info at https://www.maths.ed.ac.uk/hall/HiGHS/
    ###########################################################################

    ####################
    # GIT INSTALLATION #
    ####################

    try:

        HiGHS = git.Repo.clone_from("https://github.com/ERGO-Code/HiGHS", "HiGHS")
        os.chdir(HiGHS.working_dir)
        subprocess.check_output(["mkdir", "build"])
        os.chdir(f"{HiGHS.working_dir}/build")
        subprocess.check_output(["cmake .."], shell=True)
        subprocess.check_output("make")
        subprocess.check_output(["cp", "bin/highs", "/usr/local/bin/highs"])
        subprocess.check_output(["chmod", "+x", "/usr/local/bin/highs"])
        uid = pwd.getpwnam("airflow").pw_uid
        gid = grp.getgrnam("root").gr_gid
        highs_path = "/usr/local/bin/highs"
        os.chown(highs_path, uid, gid)

    except (error):

        print(error)

    finally:

        print("HIGHS solver installed")

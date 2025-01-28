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
        subprocess.check_output(["cmake -S . -B build"], shell=True)
        subprocess.check_output("cmake --build build", shell=True)
        os.chdir(f"{HiGHS.working_dir}/build")
        subprocess.check_output("ctest", shell=True)
        subprocess.check_output(["cp", "bin/highs", "/usr/local/bin/highs"])
        subprocess.check_output(["chmod", "+x", "/usr/local/bin/highs"])
        uid = pwd.getpwnam("cornflow").pw_uid
        gid = grp.getgrnam("root").gr_gid
        highs_path = "/usr/local/bin/highs"
        os.chown(highs_path, uid, gid)

    except error:

        print(error)

    finally:

        print("HIGHS solver installed")

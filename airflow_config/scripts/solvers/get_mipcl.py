from logging import error
import subprocess
import git
import os


def install():

    #### MIPCL ##########
    # The MIPCL installation bundle includes the MIPCL itself (the library, headers, documentation, and examples),
    # a modeling tool called MIPshell,
    # and MIPCL-PY, which is a collection of modules that allow us using MIPCL in Python programs.
    # All information about MIPCL, MIPshell, and MIPCL-PY is available on www.mipcl-cpp.appspot.com
    ####################

    ####################
    # GIT INSTALLATION #
    ####################

    try:

        MIPCL = git.Repo.clone_from("https://github.com/onebitbrain/MIPCL", "MIPCL")
        os.chdir(MIPCL.working_dir + "/bin")
        subprocess.check_output(["cp", "mps_mipcl", "/usr/local/bin/mps_mipcl"])
        subprocess.check_output(["chmod", "+x", "/usr/local/bin/mps_mipcl"])

    except (error):

        print(error)

    finally:

        print("MIPCL solver installed")

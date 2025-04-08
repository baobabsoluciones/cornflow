from logging import error
import subprocess
import git
import os
import pwd
import grp


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
        mips_path = "/usr/local/bin/mps_mipcl"
        MIPCL = git.Repo.clone_from("https://github.com/onebitbrain/MIPCL", "MIPCL")
        os.chdir(f"{MIPCL.working_dir}/bin")
        subprocess.check_output(["cp", "mps_mipcl", mips_path])
        subprocess.check_output(["chmod", "+x", mips_path])
        uid = pwd.getpwnam("cornflow").pw_uid
        gid = grp.getgrnam("root").gr_gid

        os.chown(mips_path, uid, gid)

    except error:

        print(error)

    finally:

        print("MIPCL solver installed")

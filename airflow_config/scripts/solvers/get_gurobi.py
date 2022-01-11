from logging import error
import subprocess
import os
import pwd
import grp

def install():

    #### Gurobi ###########
    # The fastest and most powerful mathematical programming solver available for your LP, QP and MIP (MILP, MIQP, and MIQCP) problems. 
    # See why so many companies are choosing Gurobi for better performance, faster development and better support.
    # More info at https://www.gurobi.com/
    ####################

    #######################
    # PYTHON INSTALLATION #
    #######################

    try:

        os.chdir("/usr/local/airflow")
        subprocess.run(
            ["wget", "https://packages.gurobi.com/9.5/gurobi9.5.0_linux64.tar.gz"]
        )
        subprocess.run(
            ["tar", "-xvf", "gurobi9.5.0_linux64.tar.gz"]
        )
        subprocess.run(
            ["mv", "gurobi950", "gurobi"]
        )       
        uid = pwd.getpwnam("airflow").pw_uid
        gid = grp.getgrnam("airflow").gr_gid
        os.chown("gurobi", uid, gid)
        os.chdir("./gurobi/linux64")
        gurobi_install = subprocess.run(
            [
                "python", "setup.py", "install"
            ],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        output_gurobi_install = gurobi_install.stdout
        print(output_gurobi_install)
        os.environ["GUROBI_HOME"] = "/usr/local/airflow/gurobi/linux64"
        os.environ["GRB_LICENSE_FILE"] = "/Library/gurobi950/gurobi.lic"

        
    except (error):

        print(error)

    finally:

        print("Gurobi optimizer installed")

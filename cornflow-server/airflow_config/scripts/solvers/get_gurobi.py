import grp
import os
import pwd
import subprocess


def install():
    """
    Gurobi: LP, QP and MIP solver.
    More info at https://www.gurobi.com/
    """
    try:
        solver_dir = os.getenv("SOLVER_DIR")
        install_dir = solver_dir + "/gurobi"
        os.chdir(solver_dir)
        subprocess.check_output(
            ["wget", "https://packages.gurobi.com/12.0/gurobi12.0.1_linux64.tar.gz"]
        )
        subprocess.check_output(["tar", "-xvf", "gurobi12.0.1_linux64.tar.gz"])
        os.rename("gurobi1201", "gurobi")
        uid = pwd.getpwnam("cornflow").pw_uid
        gid = grp.getgrnam("cornflow").gr_gid
        os.chown(install_dir, uid, gid)
        os.chdir(f"{install_dir}/linux64")
        result = subprocess.run(
            ["uv", "pip", "install", "--system", "."],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout)
        if result.returncode != 0 and result.stderr:
            print(result.stderr)
    except Exception as e:
        print(e)
    finally:
        print("Gurobi optimizer installed")

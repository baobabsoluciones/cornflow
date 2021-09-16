from logging import error
import subprocess


def install():

    #### GLPK ##########
    # The GLPK (GNU Linear Programming Kit) package is intended for solving large-scale linear programming (LP), mixed integer programming (MIP), and other related problems.
    # It is a set of routines written in ANSI C and organized in the form of a callable library.
    # More info at https://www.gnu.org/software/glpk/
    ####################

    ####################
    # PKG INSTALLATION #
    ####################

    try:

        glpk_install = subprocess.run(
            ["apt-get", "install", "-y", "glpk-utils"],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        output_glpk = glpk_install.stdout
        print(output_glpk)

    except (error):

        print(error)

    finally:

        print("glpk solver installed")

from logging import error
import subprocess

def install():

    #### CHOCO ###########
    # Choco-solver is an open-source Java library for Constraint Programming.
    # More info at https://github.com/chocoteam/choco-solver
    ######################

    ####################
    # JAR INSTALLATION #
    ####################

    try:

        choco_install = subprocess.run(['wget', 'https://github.com/chocoteam/choco-solver/releases/download/4.10.6/choco-parsers-4.10.6-jar-with-dependencies.jar', '-O','/usr/local/bin/choco.jar'], stdout=subprocess.PIPE, universal_newlines=True)
        output_choco = choco_install.stdout
        print(output_choco)
    
    except(error):

        print(error)

    finally:

        print('CHOCO solver installed')
from logging import error
import subprocess

def install():

        #### CBC ###########
        # Cbc (Coin-or branch and cut) is an open-source mixed integer linear programming solver written in C++. 
        # It can be used as a callable library or using a stand-alone executable. 
        # It can be used in a wide variety of ways through various modeling systems, packages, etc.
        # More info at https://github.com/coin-or/Cbc 
        ####################
    
        ####################
        # PKG INSTALLATION #
        ####################

    try:

        cbc_install = subprocess.run(['apt-get', 'install', '-y' , 'coinor-cbc'], stdout=subprocess.PIPE, universal_newlines=True)
        output_cbc = cbc_install.stdout
        print(output_cbc)

    except(error):

        print(error)
    
    finally:

        print('CBC solver installed')
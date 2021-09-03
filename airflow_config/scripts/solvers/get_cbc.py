import subprocess

def install():

    ####################
    # PKG INSTALLATION #
    ####################

    cbc_install = subprocess.run('sudo apt-get install -y coinor-cbc', shell=True,stdout=subprocess.PIPE, universal_newlines=True)
    output_cbc = cbc_install.stdout
    print(output_cbc)
    print('CBC solver installed')
import subprocess

def install():

    ####################
    # PKG INSTALLATION #
    ####################

    cbc_install = subprocess.run(['apt-get', 'install', '-y' , 'coinor-cbc'], stdout=subprocess.PIPE, universal_newlines=True)
    output_cbc = cbc_install.stdout
    print(output_cbc)
    print('CBC solver installed')
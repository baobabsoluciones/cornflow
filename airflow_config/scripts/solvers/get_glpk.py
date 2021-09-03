import subprocess

def install():

    ####################
    # PKG INSTALLATION #
    ####################

    glpk_install = subprocess.run(['apt-get', 'install', '-y', 'glpk-utils'], stdout=subprocess.PIPE, universal_newlines=True)
    output_glpk = glpk_install.stdout
    print(output_glpk)
    print('glpk solver installed')
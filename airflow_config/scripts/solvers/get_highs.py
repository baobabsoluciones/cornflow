import subprocess
import git
import os

def install():

    ####################
    # GIT INSTALLATION #
    ####################

    HiGHS = git.Repo.clone_from('https://github.com/ERGO-Code/HiGHS','HiGHS')
    os.chdir(HiGHS.working_dir)
    subprocess.check_output(['mkdir','build'])
    os.chdir(HiGHS.working_dir+'/build')
    subprocess.check_output(['cmake','..'])
    subprocess.check_output('make')

    print('HIGHS solver installed')
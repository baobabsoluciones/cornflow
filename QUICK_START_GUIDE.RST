=================
Quick Start Guide
=================

.. contents:: :local:

------------
Presentation
------------

This is the **contributors's quick start guide** for the **Cornflow** project. This project is divided into four directories: `Cornflow-Server <https://github.com/baobabsoluciones/cornflow-server>`_, `Cornflow-client <https://github.com/baobabsoluciones/cornflow-client>`_, `Cornflow-dags <https://github.com/baobabsoluciones/cornflow-dags-public>`_, and `Cornflow-app <https://github.com/baobabsoluciones/cornflow-app>`_. 

**Cornflow-server** allows you to run a local server on your computer, that will manage the instances of your problems, the created executions, and the communication with Airflow.

**Cornflow-dags** allows you to formalize the problems you are trying to develop a solution to.

**Cornflow-client** provides a communication interface between your computer and cornflow-server.

**Cornflow-app** provides a graphic interface that can be customized and adapted to the solvers you deploy on cornflow-dags.

-----------
First steps
-----------
The first steps to using Cornflow are to clone **Cornflow-server**, **Cornflow-dags** and **Cornflow-app** git repositories on your computer:

.. code-block:: console

  mkdir cornflow-project
  cd cornflow-project
  git clone https://github.com/baobabsoluciones/cornflow-server.git
  git clone https://github.com/baobabsoluciones/cornflow-dags-public.git
  git clone https://github.com/baobabsoluciones/cornflow-app.git

-------------
Prerequisites
-------------

Common
======

.. raw:: html

  <details open>
    <summary>Python >= 3.6 and virtual environment</summary>
    
| We recommend using a version of `Python ≥ 3.6 <https://www.python.org/downloads/>`_, along with the `Pycharm editor <https://www.jetbrains.com/fr-fr/pycharm/>`_. Please use `black code formatter <https://github.com/psf/black>`_ to format your python files. See `here <https://black.readthedocs.io/en/stable/integrations/editors.html#pycharm-intellij-idea>`_ to integrate **black** to your development environment and make it format automatically your files. 
| Once python is installed, you will need to create a virtual environment for the project: from the :code:`/cornflow-dags` directory, run: 

.. code-block:: console

    python -m venv cfvenv
    cfvenv/Scripts/activate
    
if you are working on Windows, 
or: 

.. code-block:: shell

    python -m venv cfvenv
    source cfvenv/bin/activate

in Linux.

.. raw:: html

  </details>
  
.. raw:: html

  <details open>
    <summary>Packages</summary>
    
| From then, you can install the **cornflow-client** package, required to use cornflow-server and cornflow-dags, with:

.. code-block:: console
  
    python -m pip install cornflow-client
    
For cornflow-server, you will also need the dependencies in requirements.txt:

.. code-block:: console

    python -m pip install -r cornflow-server/requirements-dev.txt

.. raw:: html

  </details>
    
For cornflow-server
===================
To run cornflow-server, you need Linux or Windows with WSL installed. 


.. raw:: html

  <details open>
    <summary>Apache-Airflow</summary>

Cornflow-server needs a running airflow server to operate. Once your virtual environment is activated, you can install airflow with pip: 

.. code-block:: shell

  pip install "apache-airflow==2.1.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.1.0/constraints-${YOUR_PYTHON_VERSION}.txt"

You will then need to install the defaults workers dependencies, to initialize the database and to create an admin user:

.. code-block:: shell

  pip install orloge cornflow_client pulp
  export AIRFLOW_HOME="$PWD/airflow_config"
  airflow db init
  airflow users create \
      --username admin \
      --firstname admin \
      --lastname admin \
      --role Admin \
      --password admin \
      --email admin@example.org

.. raw:: html

  </details>
 

..
  Docker
  ------
  You will also need to install `Docker Community Edition <https://docs.docker.com/engine/install/>`_ and `Docker Compose <https://docs.docker.com/compose/install/>`_. See `here   <https://baobabsoluciones.github.io/cornflow-server/deploy/index.html>`_ how to deploy your own cornflow server.

   
For cornflow-app
================

.. raw:: html

  <details open>
    <summary>NodeJs</summary>

| In order to develop your graphic interface with cornflow-app, you will need to have `Node v12.22 <https://nodejs.org/en/>`_ installed on your computer. The application is mainly developed in JavaScript and Vue.Js. We also recommend using `Visual Studio Code <https://code.visualstudio.com/>`_ as your IDE to code in js and vueJs.
| Once NodeJs is installed, open the terminal and navigate to the cornflow-app repository. From there, run :code:`npm install` to install the dependencies necessary to run the project. 

.. raw:: html

  </details>

---------------
Getting started
---------------
For each of the repositories, if you are going to modify the source code, you should create a new branch, by opening the terminal, navigating to the repository, and running :

.. code-block:: console

  git branch name_of_your_branch
  git checkout name_of_your_branch
  

Cornflow-server
===============

.. raw:: html

  <details open>
    <summary>Server</summary>


To launch cornflow-server, you first need to launch airflow-server. To do so, navigate to the :code:`/cornflow-dags` directory and execute the file :code:`utils/launchAirflow.sh`. 
If it is the first time you use cornflow-server, you will then need to setup cornflow's database.
    
.. code-block:: shell

  source cfvenv/bin/activate
  export FLASK_APP=cornflow.app
  export DATABASE_URL=sqlite:///cornflow.db
  python manage.py db upgrade
  python manage.py access_init
  python manage.py create_service_user  --username=airflow --email=airflow_test@admin.com --password=airflow_test_password
  python manage.py create_admin_user  --username=cornflow --email=cornflow_admin@admin.com --password=cornflow_admin_password
    
From there, you can launch cornflow-server by navigating to the cornflow-server repository and running:

.. code-block:: shell

  export FLASK_APP=cornflow.app
  export FLASK_ENV=development
  export DATABASE_URL=sqlite:///cornflow.db
  export SECRET_KEY=THISNEEDSTOBECHANGED
  export AIRFLOW_URL=http://localhost:8080
  export AIRFLOW_USER=admin
  export AIRFLOW_PWD=admin
  flask run


See the `documentation <https://baobabsoluciones.github.io/cornflow-server/main/install.html>`_ for more details on how to launch cornflow-server.

.. raw:: html

  </details>

Cornflow-dags
=============

.. raw:: html

  <details open>
    <summary>DAGs</summary>

When you start developing your solver, you will need to deploy it as a DAG, similar to the ones you can find on `cornflow-dags <https://github.com/baobabsoluciones/cornflow-dags-public>`_. 

Code
----

To do so, you need to clone the repository and create a new folder with the name of your folder in the :code:`/DAG` directory. From there, your code must have a specific architecture:

- :code:`/your_project_name`

  - :code:`/core`
  
    - :code:`instance.py`: class that contains the methods to manage the input data. Should subclass :code:`InstanceCore` from the :code:`cornflow_client` library.
    - :code:`solution.py`: class that contains the methods to manage the output data. Should subclass :code:`SolutionCore`.
    - :code:`experiment.py`: contains the methods to evaluate and validate a solution given an instance. Takes as as input an instance and a solution (that can be empty). Should subclass :code:`ExperimentCore`. 
    
  - :code:`/schemas`
  
    - :code:`instance.json`: jsonschema that describes the input data.
    - :code:`solution.json`: jsonschema that describes the output data.
    - :code:`config.json` (optional): jsonschema that describes the configuration.
    
  - :code:`/solvers`
  
    - :code:`solver1.py`
    - :code:`solver2.py` (optional)
    - ...
    
  - :code:`/data`
  
    - :code:`example_instance1`
    - ...
    
  - :code:`__init__.py`: contains a class that subclasses :code`ApplicationCore` from the library `cornflow-client`.
  - :code:`README.RST`: contains a description of the problem, of the input data and the output.

| See the `documentation <https://baobabsoluciones.github.io/cornflow-server/guides/deploy_solver_new.html>`_ for a more specific description of the requisites for each class, and feel free to check out the deployed on `cornflow-dags <https://github.com/baobabsoluciones/cornflow-dags-public>`_ for a better understanding of the structure of a dag.

Unitary tests
-------------

| When you finish developping your solver, you will need to add unit tests to validate that your solver works properly. The unit tests for your DAG should be added in the file :code:`tests/test_dags.py`, by creating a class with your project's name and following the model of the existing ones. Run :

.. code-block:: console

  python -m unittest tests.test_dags.py

to run all of the unitary tests, or, assuming that your project is name 'MyProject':

.. code-block:: console

  python -m unittest tests.test_dags.MyProject
  
to run the unitary tests of your project only.

Please refer to the `documentation <https://baobabsoluciones.github.io/cornflow-server/guides/testing_app.html>`_ for more details on the unitary tests. 

.. raw:: html

  </details>
  
  
Use your solution method
========================
Once your dag is entirely developed, you can use the cornflow-client package to access it on the server. See an example `here <https://baobabsoluciones.github.io/cornflow-server/guides/use_solver.html>`_.


Cornflow-app
============

.. raw:: html

  <details open>
    <summary>Graphic interface</summary>

In order to visualize your data with cornflow-app, you will need to add views corresponding to your problem in the code of your the application.
First, open your terminal and navigate to the cornflow-app directory. From there, run :code:`npm run dev` to start a local development server. 
Then, there are four main parts of the code that you will need to modify.

Setup
-----

- In :code:`/src/app.js`, you will need to import your application, define your routes and pages, following the model of the already defined applications.
- In the file :code:`.env`, define the variable :code:`VUE_APP_BASE_URL` as the url of your local cornflow-server. 

Data treatment
--------------
In the directory :code:`/src/apps`, create a directory with the name of your project. This directory should contain at least three files:

- :code:`instance.js`
- :code:`solution.js`
- :code:`experiment.js`

Those three files have the same objectives than the :code:`instance.py`, :code:`solution.py` and :code:`experiment.py` defined in your DAG. They are the core of your project, and allow to realize operations with your input data, your output data, or both. They should respectively inherit the classes :code:`InstanceCore`, :code:`SolutionCore` and :code:`ExperimentCore` defined in :code:`/src/core`.

Views
-----
In the directory :code:`/src/views/apps`, you will need to add your views, computed from the data contained in your Instance, Solution and Experiment classes.
To do so, you must create a directory with the name of your project, and put your files in that directory.

Unitary tests
-------------
In the directory :code:`/tests/unit`, you should define a new directory :code:`my_project`. In this directory, you should define unitary tests that will test that your application works correctly. You can follow the example of the unitary tests of the other projects. The data needed to execute the tests should be put in the directory :code:`/tests/data`.

.. raw:: html

  </details>
  
-------------
Contributions
-------------
Contribute
==========
| If you wish to contribute to the project, you can open a pull request to propose your changes.
| In that case, please make sure that your code respects the coding style and rules described `here <https://baobabsoluciones.github.io/cornflow-server/guides/coding_style.html>`_ and that you applied the black formatter.



Report bugs
===========
Report bugs through `GitHub <https://github.com/baobabsoluciones/cornflow-server/issues>`_. Please check that the issues has not been reported before, and, if it has not, please report only relevant issues and try to join code that produces those bugs.



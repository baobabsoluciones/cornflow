Cornflow
=========

The aim of this repository is to create an open source optimization server.

Requirements
~~~~~~~~~~~~~~~~~~

* Linux or Windows with WSL
* python >= 3.5
* postgresql

Install cornflow
~~~~~~~~~~~~~~~~~~

cornflow consists of two projects: cornflow (itself) and airflow (from apache). They are conceived to be deployed independently. Here we will explain the "development deploy" that consists on installing them in two python virtual environments in the same machine.

do::

    git clone git@github.com:ggsdc/corn.git
    cd corn
    python3 -m venv cfvenv
    cfvenv/bin/pip3 install -r requirements.txt


Setup cornflow database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You now need to create a user and password in postgresql (we will be using `postgres` and `postgresadmin`). And also you need to create a database (we will be using one with the name `cornflow`).

Create a new user::

    sudo -u postgres psql

In the shell you put the following::

    ALTER USER postgres PASSWORD 'postgresadmin';
    \q

Create a new database::

    sudo su - postgres
    psql -c "create database cornflow"
    exit

Every time cornflow is used, PostgreSQL and airflow needs to be configured::

    export FLASK_APP=flaskr.app
    export FLASK_ENV=development
    export DATABASE_URL=postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow
    export SECRET_KEY=THISNEEDSTOBECHANGED
    export AIRFLOW_URL=http://localhost:8080
    export CORNFLOW_URL=http://localhost:5000

In windows use ``set`` instead of ``export``.

In order to create the database, execute the following::

    source cfvenv/bin/activate
    python manage.py db init
    python manage.py db migrate
    python manage.py db upgrade
    python manage.py create_super_user

Starting flask server
~~~~~~~~~~~~~~~~~~~~~~~

Each time you run the flask server, execute the following::

    source cfvenv/bin/activate
    export FLASK_APP=flaskr.app
    export FLASK_ENV=development
    export DATABASE_URL=postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow
    export SECRET_KEY=THISNEEDSTOBECHANGED
    export AIRFLOW_URL=http://localhost:8080
    flask run


Install and configure airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need your own virtual environment for airflow to work.

**On Linux**

Install it::

    cd corn
    python3 -m venv afvenv
    afvenv/bin/pip3 install -r requirements_af.txt
    export AIRFLOW_HOME="$PWD/airflow_config"
    airflow -h

If you want to use postgresql with airflow too you need to edit the existing values in airflow config (corn/airflow_config/airflow.cfg)::

    sql_alchemy_conn = postgres://postgres:postgresadmin@127.0.0.1:5432/airflow

In the same file, if you do not want the examples::

    load_examples = False

Create the `airflow` database in postgresql::

    sudo su - postgres
    psql -c "create database airflow"
    exit


initialize the database::

    airflow initdb

Reset the database (if necessary, I did not need this)::

    airflow resetdb

If necessary, give execution rights to your user in the airflow folder (I did not need this)::

    sudo chmod -R  a+rwx airflow

**On windows**

- Install Linux subsystems for linux: https://docs.microsoft.com/es-es/windows/wsl/install-win10
- Install Ubuntu from windows store
- Install python in Ubuntu and follow Linux installations instructions above.

Launch airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

start the web server, default port is 8080::

    cd corn
    source afvenv/bin/activate
    export AIRFLOW_HOME="$PWD/airflow_config"
    airflow webserver -p 8080 &

start the scheduler::

    airflow scheduler &

airflow gui will be at::

    localhost:8080

Select the DAG in the web and click on ON.

Killing airflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Search for the code of the process in Linux::

    ps aux | grep airflow

Kill it::

    kill -9 CODE

If you're filling lucky::
    
    kill -9 $(ps aux | grep 'airflow' | awk '{print $2}')

Using cornflow
~~~~~~~~~~~~~~~~~~

Launch airflow and the flask server from two different terminals (using their respective virtual environments).

In order to use cornflow api, import api functions::

    from airflow_config.dags.api_functions import *

Create a user::

    sign_up(email, pwd, name)

log in::

    token = login(email, pwd)

create and log in as airflow user ( necessary until airflow is made a superuser)::

    sign_up(email="airflow@noemail.com", pwd="airflow", name="airflow")
    token = login(email="airflow@noemail.com", pwd="airflow")

create an instance::
    
    import pulp
    prob = pulp.LpProblem("test_export_dict_MIP", pulp.LpMinimize)
    x = pulp.LpVariable("x", 0, 4)
    y = pulp.LpVariable("y", -1, 1)
    z = pulp.LpVariable("z", 0, None, pulp.LpInteger)
    prob += x + 4 * y + 9 * z, "obj"
    prob += x + y <= 5, "c1"
    prob += x + z >= 10, "c2"
    prob += -y + z == 7.5, "c3"
    data = prob.to_dict()

    instance_id = create_instance(token, data)

Solve an instance::

    config = dict(
        solver = "PULP_CBC_CMD",
        mip = True,
        msg = True,
        warmStart = True,
        timeLimit = 10,
        options = ["donotexist", "thisdoesnotexist"],
        keepFiles = 0,
        gapRel = 0.1,
        gapAbs = 1,
        maxMemory = 1000,
        maxNodes = 1,
        threads = 1,
        logPath = "test_export_solver_json.log"
    )
    execution_id = create_execution(token, instance_id, config)

Retrieve a solution::

    data = get_data(token, execution_id)


Run an execution in airflow api (not needed)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The execution id has to be passed like this::

    conf = "{\"exec_id\":\"%s\"}" % execution_id

    response = requests.post(
        "http://localhost:8080/api/experimental/dags/solve_model_dag/dag_runs",
        json={"conf":conf})


Deploying to heroku
~~~~~~~~~~~~~~~~~~~~~~~

create app::
    
    heroku git:remote -a 'cornflow'
    heroku buildpacks:add heroku/python --app 'cornflow'
    heroku addons:create heroku-postgresql:hobby-dev --app 'cornflow'
    heroku config:set SECRET_KEY='some-secret-string' --app 'cornflow'
    git push heroku master
    heroku run python manage.py migrate


Deploying with docker-compose
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The docker-compose.yml file write in version '3' of the syntaxis describes the build of four docker containers::

	app python3 cornflow service
	airflow service based on puckel/docker-airflow image
	cornflow postgres database service
	airflow postgres database service

create containers::

	docker-compose up --build -d
	
list containers::

	docker-compose ps

inspect container::

	docker exec -it containerid bash

stop containers::

	docker-compose down
	
destroy all container and images (be carefull! this destroy all docker images of non running container)::

	docker system prune -af

cornflow app  "http://localhost:5000"
airflow GUI  "http://localhost:8080"

Deploying with Vagrantfile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install Vagrant by Hashicorp "https://www.vagrantup.com/intro"

Install Oracle VM VirtualBox "https://www.virtualbox.org/"

The Vagrantfile in root folder describes a Ubuntu bionic x64 dummy box with 2Gb of RAM and IP = '192.168.33.10' Please, change to your favourite features or docker-compose supported machine.

Once previously steps has done, deploy a virtual machine in your computer with these command from root corn folder::

	vagrant up
	
if you have already deploy the machine you can access it with ::

	vagrant ssh
	
suspend the machine with::

	vagrant halt
	
destroy the machine with::

	vagrant destroy -f

cornflow app  "http://vagrantfileIP:5000"
airflow GUI  "http://vagrantfileIP:8080"

Deploying in Ubuntu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open the VagrantFile and copy the instructions at the beginning in the console. Except the last line "cd /vagrant" and instead do::

    sudo docker-compose up -d --build

Then follow the instructions in "Deploying with docker-compose".

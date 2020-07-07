# Cornflow

The aim of this repository is to create an open source optimization server.

## How to run it lcoally

### Execute this commands once

py manage.py db init
py manage.py db migrate
py manage.py db upgrade

### Execute this commands befor starting the server up

set FLASK_APP=flaskr.app
set FLASK_ENV=development
set DATABASE_URL=postgres://postgres:postgresadmin@127.0.0.1:5432/cornflow
set SECRET_KEY=THISNEEDSTOBECHANGED
flask run

### Run an execution in airflow api

The execution id has to be passed like this:

<code>conf = "{\"exec_id\":\"%s\"}" % execution_id

response = requests.post(
        "http://localhost:8080/api/experimental/dags/solve_model_dag/dag_runs",
        json={"conf":conf})</code>

#!/usr/bin/env bash
# Cornflow init script for Dockerfile ENTRYPOINT

# Global defaults and back-compat
: "${AIRFLOW_USER:="admin"}"
: "${AIRFLOW_PWD:="admin"}"
: "${AIRFLOW_URL:="http://webserver:8080"}"
: "${CORNFLOW_URL:="http://cornflow:5000"}"
: "${FLASK_APP:="cornflow.app"}"
: "${FLASK_ENV:="development"}"
#: "${SECRET_KEY=${FERNET_KEY:=$(python -c "from cryptography.fernet import Fernet; FERNET_KEY = Fernet.generate_key().decode(); print(FERNET_KEY)")}}"

export \
  AIRFLOW_USER \
  AIRFLOW_PWD \
  AIRFLOW_URL \
  CORNFLOW_URL \
  FLASK_APP \
  FLASK_ENV \

# check database param from docker env
if [ -z "$DATABASE_URL" ];  then

     >&2 printf '%s\n' "FATAL: you need to provide a postgres database for Cornflow"
     exit 1
	 
fi

# make initdb and migrations in db
python manage.py db init
python manage.py db migrate
python manage.py db upgrade
python manage.py create_super_user

# Cambiar flask por Gunicorn
#flask run -h 0.0.0.0

/usr/local/bin/gunicorn -c gunicorn.py "cornflow:create_app('$FLASK_ENV')" --log-level info

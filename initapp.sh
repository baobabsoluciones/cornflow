#!/usr/bin/env bash
# Cornflow init script for Dockerfile ENTRYPOINT

# Global defaults and back-compat
: "${AIRFLOW_USER:="admin"}"
: "${AIRFLOW_PWD:="admin"}"
: "${AIRFLOW_URL:="http://webserver:8080"}"
: "${CORNFLOW_URL:="http://cornflow:5000"}"
: "${FLASK_APP:="cornflow.app"}"
: "${FLASK_ENV:="development"}"
: "${SECRET_KEY=${FERNET_KEY:=$(python -c "from cryptography.fernet import Fernet; FERNET_KEY = Fernet.generate_key().decode(); print(FERNET_KEY)")}}"
: "${DATABASE_URL=${CORNFLOW_DB_CONN}}"
: "${ADMIN_USER:="user@cornflow.com"}"
: "${ADMIN_PWD:="cornflow1234"}"

export \
  AIRFLOW_USER \
  AIRFLOW_PWD \
  AIRFLOW_URL \
  ADMIN_USER \
  ADMIN_PWD \
  CORNFLOW_DB_CONN \
  CORNFLOW_URL \
  DATABASE_URL \
  FLASK_APP \
  FLASK_ENV \
  SECRET_KEY \
  CORNFLOW_LDAP_ENABLE \
  LDAP_PROTOCOL_VERSION \
  LDAP_BIND_PASSWORD \
  LDAP_BIND_DN \
  LDAP_USE_TLS \
  LDAP_HOST \
  LDAP_USERNAME_ATTRIBUTE \
  LDAP_USER_BASE \
  LDAP_EMAIL_ATTRIBUTE \
  LDAP_USER_OBJECT_CLASS

# check database param from docker env
if [ -z "$CORNFLOW_DB_CONN" ];  then
    # Default values corresponding to the default compose files
	: "${CORNFLOW_DB_HOST:="cornflow_db"}"
	: "${CORNFLOW_DB_PORT:="5432"}"
	: "${CORNFLOW_DB_USER:="cornflow"}"
	: "${CORNFLOW_DB_PASSWORD:="cornflow"}"
	: "${CORNFLOW_DB:="cornflow"}"

    DATABASE_URL="postgres://${CORNFLOW_DB_USER}:${CORNFLOW_DB_PASSWORD}@${CORNFLOW_DB_HOST}:${CORNFLOW_DB_PORT}/${CORNFLOW_DB}"
    export DATABASE_URL
fi

if [[ -z "$DATABASE_URL" ]]; then
	 >&2 printf '%s\n' "FATAL: you need to provide a postgres database for Cornflow"
     exit 1
fi

# Check LDAP parameters for active directory
if [ "$CORNFLOW_LDAP_ENABLE" = "True" ]; then
  # Default values corresponding to the default compose files
    : "${LDAP_PROTOCOL_VERSION:="3"}"
    : "${LDAP_BIND_PASSWORD:="adminldap"}"
    : "${LDAP_BIND_DN:="cn=admin,dc=cornflow,dc=com"}"
    : "${LDAP_USE_TLS:="False"}"
    : "${LDAP_HOST:="ldap://openldap:389"}"
    : "${LDAP_USERNAME_ATTRIBUTE:="cn"}"
    : "${LDAP_USER_BASE:="dc=cornflow,dc=com"}"
    : "${LDAP_EMAIL_ATTRIBUTE:="mail"}"
    : "${LDAP_USER_OBJECT_CLASS:="top"}"
  >&2 printf '%s\n' "Cornflow will be deployed with LDAP Authorization. Please review your ldap auth configuration."
fi

# make initdb and/or migrations
python manage.py db upgrade
# create airflow superuser
python manage.py create_super_user --user="$ADMIN_USER" --password="$ADMIN_PWD"

# execute gunicorn with config file "gunicorn.py"
/usr/local/bin/gunicorn -c cornflow/gunicorn.py "cornflow:create_app('$FLASK_ENV')"

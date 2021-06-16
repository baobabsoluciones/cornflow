#!/usr/bin/env bash
# Cornflow init script for Dockerfile ENTRYPOINT

# Global defaults and back-compat
: "${AIRFLOW_USER:="admin"}"
: "${AIRFLOW_PWD:="admin"}"
: "${AIRFLOW_URL:="http://webserver:8080"}"
: "${CORNFLOW_URL:="http://cornflow:5000"}"
: "${AUTH_TYPE:="1"}"
: "${FLASK_APP:="cornflow.app"}"
: "${FLASK_ENV:="development"}"
: "${SECRET_KEY=${FERNET_KEY:=$(python -c "from cryptography.fernet import Fernet; FERNET_KEY = Fernet.generate_key().decode(); print(FERNET_KEY)")}}"
: "${DATABASE_URL=${CORNFLOW_DB_CONN}}"
: "${CORNFLOW_ADMIN_USER:="cornflow_admin"}"
: "${CORNFLOW_ADMIN_EMAIL:="cornflow_admin@cornflow.com"}"
: "${CORNFLOW_ADMIN_PWD:="cornflowadmin1234"}"
: "${CORNFLOW_SERVICE_USER:="service_user"}"
: "${CORNFLOW_SERVICE_EMAIL:="service_user@cornflow.com"}"
: "${CORNFLOW_SERVICE_PWD:="serviceuser1234"}"

export \
  AIRFLOW_USER \
  AIRFLOW_PWD \
  AIRFLOW_URL \
  CORNFLOW_ADMIN_USER \
  CORNFLOW_ADMIN_EMAIL \
  CORNFLOW_ADMIN_PWD \
  CORNFLOW_SERVICE_USER \
  CORNFLOW_SERVICE_EMAIL \
  CORNFLOW_SERVICE_PWD \
  CORNFLOW_DB_CONN \
  CORNFLOW_URL \
  DATABASE_URL \
  FLASK_APP \
  FLASK_ENV \
  CORNFLOW_LOGGING \
  SECRET_KEY \
  AUTH_TYPE

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
if [ "$AUTH_TYPE" = "2" ]; then
  # Default values corresponding to the default compose files
    : "${LDAP_PROTOCOL_VERSION:="3"}"
    : "${LDAP_BIND_PASSWORD:="admin"}"
    : "${LDAP_BIND_DN:="cn=admin,dc=example,dc=org"}"
    : "${LDAP_USE_TLS:="False"}"
    : "${LDAP_HOST:="ldap://openldap:389"}"
    : "${LDAP_USERNAME_ATTRIBUTE:="cn"}"
    : "${LDAP_USER_BASE:="ou=users,dc=example,dc=org"}"
    : "${LDAP_EMAIL_ATTRIBUTE:="mail"}"
    : "${LDAP_USER_OBJECT_CLASS:="inetOrgPerson"}"
    : "${LDAP_GROUP_OBJECT_CLASS:="posixGroup"}"
    : "${LDAP_GROUP_ATTRIBUTE:="cn"}"
    : "${LDAP_GROUP_BASE:="ou=groups,dc=example,dc=org"}"
    : "${LDAP_GROUP_TO_ROLE_SERVICE:="service"}"
    : "${LDAP_GROUP_TO_ROLE_ADMIN:="administrators"}"
    : "${LDAP_GROUP_TO_ROLE_VIEWER:="viewers"}"
    : "${LDAP_GROUP_TO_ROLE_PLANNER:="planners"}"
  >&2 printf '%s\n' "Cornflow will be deployed with LDAP Authorization. Please review your ldap auth configuration."
  export \
    LDAP_PROTOCOL_VERSION \
    LDAP_BIND_PASSWORD \
    LDAP_BIND_DN \
    LDAP_USE_TLS\
    LDAP_HOST \
    LDAP_USERNAME_ATTRIBUTE \
    LDAP_USER_BASE \
    LDAP_EMAIL_ATTRIBUTE \
    LDAP_USER_OBJECT_CLASS \
    LDAP_GROUP_OBJECT_CLASS \
    LDAP_GROUP_ATTRIBUTE \
    LDAP_GROUP_BASE \
    LDAP_GROUP_TO_ROLE_SERVICE \
    LDAP_GROUP_TO_ROLE_ADMIN \
    LDAP_GROUP_TO_ROLE_VIEWER \
    LDAP_GROUP_TO_ROLE_PLANNER
fi

if [ "$CORNFLOW_LOGGING" == "file" ]; then
  cat > /etc/logrotate.d/cornflow <<EOF
   /usr/src/app/log/*.log {
          rotate 30
          daily
          compress
          size 20M
          postrotate
              kill -HUP \$(cat /usr/src/app/gunicorn.pid)
          endscript
  }
EOF
fi

# make initdb and/or migrations
python manage.py db upgrade
# make initdb access control
python manage.py access_init

# create user if auth type is db
if [ "$AUTH_TYPE" = "1" ]; then
  # create cornflow admin user
  python manage.py create_admin_user --username="$CORNFLOW_ADMIN_USER" --email="$CORNFLOW_ADMIN_EMAIL" --password="$CORNFLOW_ADMIN_PWD"
  # create cornflow service user
  python manage.py create_service_user --username="$CORNFLOW_SERVICE_USER" --email="$CORNFLOW_SERVICE_EMAIL" --password="$CORNFLOW_SERVICE_PWD"
fi

# execute gunicorn with config file "gunicorn.py"
/usr/local/bin/gunicorn -c cornflow/gunicorn.py "cornflow:create_app('$FLASK_ENV')"

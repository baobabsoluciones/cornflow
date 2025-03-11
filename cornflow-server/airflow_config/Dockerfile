# AIRFLOW VERSION 2.9.1
# AUTHOR: cornflow@baobabsoluciones.es
# DESCRIPTION: Airflow 2.9.1 image personalized for use with Cornflow (from baobabsoluciones/pysolver image)
# baobab code version is 1.1.5

FROM baobabsoluciones/pysolver:1.1
LABEL maintainer="cornflow@baobabsoluciones"

# Never prompt the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# Airflow vars
ARG AIRFLOW_VERSION=2.9.1
ARG AIRFLOW_USER_HOME=/usr/local/airflow
ARG CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-3.10.txt"
ARG AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW_HOME=${AIRFLOW_USER_HOME}

# install Airflow and extras: celery,postgres and redis
RUN pip install "apache-airflow[amazon,celery,google,postgres,redis,sendgrid]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
# We add these overruns due to security reasons as suggested here: https://airflow.apache.org/docs/apache-airflow/stable/installation/installing-from-pypi.html#upgrading-and-installing-dependencies-including-providers
RUN pip install "apache-airflow[amazon,celery,google,postgres,redis,sendgrid]==${AIRFLOW_VERSION}" "cryptography==42.0.5" "requests==2.31.0" "Werkzeug==2.3.8"

# copy init script and config to container
COPY scripts ${AIRFLOW_HOME}/scripts
COPY plugins ${AIRFLOW_HOME}/plugins
COPY webserver_ldap.py ${AIRFLOW_HOME}/webserver_ldap.py

# create folder for custom ssh keys
RUN mkdir ${AIRFLOW_HOME}/.ssh

# rights for user cornflow on application
RUN chown -R cornflow: ${AIRFLOW_HOME}

EXPOSE 8080 5555 8793

# change user to cornflow
USER cornflow
WORKDIR ${AIRFLOW_HOME}

ENTRYPOINT ["python", "scripts/init_airflow_service.py"]
CMD ["webserver"]
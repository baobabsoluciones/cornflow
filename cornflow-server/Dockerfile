# VERSION 1.1.0
# AUTHOR: sistemas@baobabsoluciones.es

FROM python:3.10-slim-buster
LABEL maintainer="cornflow@baobabsoluciones"

# Never prompt the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# CORNFLOW vars
ARG CORNFLOW_VERSION=1.1.5

# install linux pkg
RUN apt update -y && apt-get install -y --no-install-recommends \
		gcc \
		git \
        ssh \
		python3-dev \
		libffi-dev \
		libpq-dev \
		logrotate
		
# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEFAULT_POSTGRES=1

# install dependencies
RUN pip install --upgrade pip
RUN pip install "cornflow==${CORNFLOW_VERSION}"


# create folder for logs
RUN mkdir -p /usr/src/app/log

# create folder for custom ssh keys
RUN mkdir /usr/src/app/.ssh

# user cornflow on application
RUN useradd -ms /bin/bash -d /usr/src/app cornflow
RUN chown -R cornflow: /usr/src/app
USER cornflow

EXPOSE 5000

# execute python init script
CMD ["cornflow", "service", "init"]

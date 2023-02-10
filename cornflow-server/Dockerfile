# VERSION 2.0.2
# AUTHOR: sistemas@baobabsoluciones.es

FROM python:3.8-slim-buster
LABEL maintainer="sistemas@baobabsoluciones"

# Never prompt the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# CORNFLOW vars
ARG CORNFLOW_VERSION=1.0.0

# install linux pkg
RUN apt update -y && apt-get install -y --no-install-recommends \
		gcc \
		git \
		python3-dev \
		libffi-dev \
		libpq-dev \
		logrotate
		
# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
RUN pip install "git+https://github.com/baobabsoluciones/cornflow@feature/package#subdirectory=cornflow-server"


RUN mkdir -p /usr/src/app/log

EXPOSE 5000

# execute python init script
CMD ["init_cornflow_service"]

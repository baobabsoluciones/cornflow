Deployment
==============

From the beginning of the project, we thought that the best way to offer a cornflow deployment would be through container technology. Following the agile methodology allows us to translate the development to any system in a precise and immutable way. We will continue to work to provide a kubernetes installation template and other code-infrastructure deployment methods.
In `this repository <https://github.com/baobabsoluciones/corn>`_ you can find various templates for `docker-compose <https://docs.docker.com/compose/>`_ in which to test different types of deployment.

The ``docker-compose.yml`` describes the build of this services:

#. cornflow application server
#. postgresql server for cornflow and airflow internal database
#. airflow webserver and scheduler server

.. _cornflow_docker_stack:

.. figure:: ./../_static/cornflow_docker_stack.png

   Since to run cornflow it is essential to have the airflow application, the ``docker-compose.yml`` file includes a deployment of said platform.


Contents:

.. toctree::
    :maxdepth: 3

    intro
    docker-compose.yml
    docker-stack
    simultaneous
    options
    production
    access
    logs

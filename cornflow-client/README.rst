Cornflow client
================

The aim of this repository is to have a client to use to connect to a deployed cornflow webserver

Requirements
~~~~~~~~~~~~

* python >= 3.6

Install cornflow-client
~~~~~~~~~~~~~~~~~~~~~~~~

To install the package do::

    py -m pip install cornflow-client

Use cornflow-client
~~~~~~~~~~~~~~~~~~~~

To use, first you have to import the package::

    from cornflow_client import CornFlow

Then you have to start up the client and login or sing up::

    client = CornFlow(url="URL_TO_THE_WEB_SERVER")
    client.sing_up(email, password, name)
    client.login(email, password)

And then finally you can use the cornflow webserver and start solving problems::

    instance_id = client.create_instance(data)
    execution_id = client.create_execution(instance_id, execution_config)
    status = client.get_status(execution_id)
    results = client.get_results(execution_id)

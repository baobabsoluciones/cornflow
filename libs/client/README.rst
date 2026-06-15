cornflow client
================

The aim of this repository is to have a client to use to connect to a deployed cornflow webserver

Requirements
~~~~~~~~~~~~

* Python >= 3.10

Install cornflow-client
~~~~~~~~~~~~~~~~~~~~~~~~

From PyPI::

    uv pip install cornflow-client

From source (development): from the ``libs/client`` directory::

    uv sync --extra dev

This creates a virtual environment (``.venv``) and installs the project. Run commands with ``uv run <command>``. See `uv documentation <https://docs.astral.sh/uv/>`_.

Use cornflow-client
~~~~~~~~~~~~~~~~~~~~

To use, first you have to import the package::

    from cornflow_client import CornFlow

Then you have to start up the client and login or sing up::

    client = CornFlow(url="URL_TO_THE_WEB_SERVER")
    client.sign_up(username, email, password)
    client.login(username, password)

And then finally you can use the cornflow webserver and start solving problems::

    instance_id = client.create_instance(data)
    execution_id = client.create_execution(instance_id, execution_config)
    status = client.get_status(execution_id)
    results = client.get_results(execution_id)

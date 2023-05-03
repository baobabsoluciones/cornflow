==============
Cornflow-tools
==============

Cornflow-core is a library that contains modules to help you create REST APIs in an easier and faster way.
It includes a set of modules that can be used to start the creation of your flask REST API and some command line
interface commands that let you create a full REST API from a JSONSchema file that represent your data or
create a JSONSchema file representing your REST API.

----------------------------------------------------
Command line interface :code:`generate_from_schema`
----------------------------------------------------
The cli :code:`generate_from_schema` allows you to automatically generate models, endpoints and schemas
from a JSONSchema. The generated files can then be added to your flask (RestFul) REST API.

How to use?
===========

To start, you need to have a json file containing the schema of the tables you want to create.
It is possible to generate this json schema from an Excel file with the function
:code:`schema_from_excel` from :code:`cornflow-client`.

Let's assume that this file is stored on your computer as :code:`C:/Users/User/instance.json`
Open the terminal, then run:

.. code-block:: console

    generate_from_schema -p C:/Users/User/instance.json -a application_name

The argument :code:`application_name` will be the prefix of the name used for the generated files, classes
and tables. It is an optional argument
This command will create a new :code:`output/` directory in the folder where is executed, containing three
directories :code:`models/`, :code:`schemas/` and :code:`endpoints/`, in which the new files will be added.

Optional arguments
==================

Output path
-----------

Use the :code:`-o` or :code:`--output-path` options to set an output path for the files. The
directories :code:`models/`, :code:`endpoint/` and :code:`schemas/` will be created directly in that
direction instead of the :code:`./output/` directory.

Example:

.. code-block:: console

    generate_from_schema -p C:/Users/User/instance.json -a application_name --output-path C:/Users/User/output_files


Remove methods
--------------

By default, two endpoints are created:

- A global endpoint, with two methods:
    - :code:`get()`, that returns all the element of the table.
    - :code:`post(**kwargs)`, that adds a new row to the table.
- A detail endpoint, with four methods:
    - :code:`get(idx)`, that returns the entry with the given id.
    - :code:`put(idx, **kwargs)`, that updates the entry with the given id with the given data.
    - :code:`patch(idx, **kwargs)` that patches the entry with the given id with the given oatch.
    - :code:`delete(idx)`, that deletes the entry with the given id.
- A bulk endpoint, with two methods:
    - :code:`post(**kwargs)`, that adds several new rows to the table.
    - :code:`put(**kwargs)`, that adds or updates several rows in the table.

If one or several of those methods are not necessary, the option :code:`--remove-methods` or :code:`-r` allows to not
generate some of those methods. 

Example:

.. code-block:: console

    generate_from_schema -p C:/Users/User/instance.json -a application_name --remove-methods get-list -r delete-detail

In that example, for each table, the detail endpoint will not contain the :code:`delete()` method and
the list endpoint will not contain the :code:`get()` method. The choices for this method are
:code:`get-list`, :code:`post-list`, :code:`get-detail`, :code:`put-detail`, :code:`delete-detail`,
:code:`patch-detail`, :code:`post-bulk` and :code:`put-bulk`.

One table
---------

By default, the module accepts schemas that contain several tables at once (see for example the
instance schema for the rostering application, in **cornflow-dags**). If you only need to create one table,
the schema can also have the following format:

.. code-block::

    {
      "type": "array",
      "description": "Table with the employee master information",
      "items": {
        "type": "object",
        "properties": {
          "id": {
            "description": "The unique identifier for each employee.",
            "type": "integer",
          },
          "name": {
            "description": "The name of each employee.",
            "type": "string",
          },
        },
        "required": [
          "id",
          "name",
        ]
      }
    }

that is, the schema is simply the description of the table. In that case, you can use
the :code:`--one` option to indicate the name of the table. If not, the generated table will be called
:code:`{application_name}_data` by default.

Example:

.. code-block:: console

    generate_from_schema -p C:/Users/User/instance.json -a application_name --one table_name

In that case, only one table will be created.

Endpoints methods
-----------------
Use the :code:`-m` or :code:`--endpoints_methods` to pass an optional json file to the function.
In this file, you may list the methods you want to create for every table.

Example:

.. code-block:: python

    generate_from_schema -p C:/Users/User/instance.json -m C:/Users/User/endpoints_methods.json

The format of the json file must be the following:

.. code-block:: json

    {
        "table1":["get_list", "post_list"],
        "table2":["post_list", "get_detail", "put_detail"]
    }

Roles whith access to the endpoints
-----------------
Use the :code:`-e` or :code:`--endpoints_access` to pass an optional json file to the function.
In this file, you may list the roles which should be able to access each table endpoint.
The available roles are:

.. code-block:: python

    ["VIEWER_ROLE", "PLANNER_ROLE", "ADMIN_ROLE", "SERVICE_ROLE"]

Example:

.. code-block:: python

    generate_from_schema -p C:/Users/User/instance.json -e C:/Users/User/endpoints_access.json

The format of the json file must be the following:

.. code-block:: json

    {
        "table1":["VIEWER_ROLE", "SERVICE_ROLE"],
        "table2":["VIEWER_ROLE", "PLANNER_ROLE", "ADMIN_ROLE", "SERVICE_ROLE"]
    }

Notes
=====
Primary keys
------------

If your table contains a field named :code:`id`, this field will automatically be considered the
primary key of the table. If it doesn't, an autoincrementing column :code:`id` will be added to the
table and :code:`id` will be set as the primary key of the table.

Foreign keys
------------
If a field is a foreign key to another table, this can be indicated in the schema.
You only need to add the property :code:`foreign_key` in the information about the property.
Its value must have the format :code:`table_name.key`, :code:`table_name` being the name of the table
the attributes refers to, and :code:`key` being the name of the foreign key in the original table.
For example, if the table employee has a :code:`id_job` property that is a foreign_key referring to
the property :code:`id` of the table :code:`jobs`, then the property :code:`id_job` can be described
as follows:

.. code-block::

    {
        ...,
        "id_job": {
            "type": "integer",
            "description": "The id. of the job",
            "foreign_key": "jobs.id"
        },
        ...
    }

If the property :code:`foreign_key` is left empty, it is assumed that the key is not a foreign key.

Date formats
-------------
By default, json doesn't accept datetimes formats, they must be passed as strings.
However, it is possible to pass this information through the format property and have flask models created
with date columns.
You only need to add the property :code:`format` in the information about the property.
The formats which are currently taken into account are "date", "time" and "datetime".

.. code-block::

    {
        ...,
        "current_date": {
            "type": "string",
            "format": "datetime",
        },
        ...
    }

-----------------------------------
Module :code:`schema_from_models`
-----------------------------------
The cli :code:`schema_from_models` allows you to automatically generate a JSONSchema based on
a set of models.

How to use?
===========

To start, you need to have a directory containing the SQLAlchemy models.
Let's assume that this directory is stored on your computer as :code:`C:/Users/User/models`
Open the terminal and run:

.. code-block:: console

    schema_from_models -p C:/Users/User/models

This command will create a new :code:`output_schema.json` directory in the directory from where it was executed,
containing the generated schema.


Optional arguments
==================

Output path
-----------

Specify an output path using the argument :code:`-o` or :code:`--output_path`.

Ignore files
------------

By default, all the python files that do not contain models will be ignored. However, if you
need to specify that some model files need to be ignored, you can use the :code:`-i` or
:code:`--ignore-files` option. This option takes as arguments the name of the files to ignore
with their extension. Example:

.. code-block:: console

    schema_from_models -p C:/Users/User/models --ignore-files instance.py -i execution.py

----------------------------------------------------
Generating endpoints, models and schemas from Excel
----------------------------------------------------

cornflow_client library include a function to generate schema from an Excel file containing example data.
Using this function in combination with :code`generate_from_schema` it is possible to generate all the
database structure directly from Excel.
This can be achieved using the following script:

.. code-block::

    from click.testing import CliRunner
    from cornflow_client.schema.tools import schema_from_excel
    from cornflow_core.cli.generate_from_schema import generate_from_schema

    path = "../data/"
    excel_path = path + "table_structure.xlsx"
    schema_path = path + "data_schema.json"
    path_methods = path + "endpoints_methods.json"
    path_access = path + "endpoints_access.json"
    path_output = "../project_name/"

    # create schema from excel
    schema = schema_from_excel(
        excel_path,
        path_out=schema_path,
        fk=True,
        format=True,
        path_access=path_access,
        path_methods=path_methods,
    )

    # create endpoints from schema
    runner = CliRunner()
    result = runner.invoke(
        generate_from_schema,
        ["-p", schema_path, "-o", path_output, "-m", path_methods, "-e", path_access],
    )


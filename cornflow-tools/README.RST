==============
Cornflow-tools
==============

Cornflow-tools is a library that contains modules to help you adapt cornflow to your needs

-----------------------------------
Module :code:`generate_from_schema`
-----------------------------------
The module :code:`generate_from_schema` allows you to automatically generate models, endpoints and schemas
from a JSONSchema. The generated files can then be added to **cornflow-server**.

How to use?
===========

To start, you need to have a json file containing the schema of the tables you want to create.
Let's assume that this file is stored on your computer as :code:`C:/Users/User/instance.json`
Open the terminal and navigate to the **cornflow-tools** directory. From there, run:

.. code-block:: console

    python generate_from_schema C:/Users/User/instance.json application_name

The argument :code:`application_name` will be the prefix of the name used for the generated files, classes
and tables.
This command will create a new :code:`output/` directory in **cornflow-tools**, containing three
directories :code:`models/`, :code:`schemas/` and :code:`endpoints/`, in which the new files will be added.

Optional arguments
==================

Output path
-----------

Use the :code:`-op` or :code:`--output_path` options to set an output path for the files. The
directories :code:`models/`, :code:`endpoint/` and :code:`schemas/` will be created directly in that
direction instead of the :code:`cornflow-tools/output/` directory.

Example:

.. code-block:: console

    python generate_from_schema C:/Users/User/instance.json application_name --output_path C:/Users/User/output_files


Remove methods
--------------

By default, two endpoints are created:

- A global endpoint, with three methods:
    - :code:`get()`, that returns all the element of the table
    - :code:`post(**kwargs)`, that adds a new row to the table
    - :code:`delete()`, that deletes all the rows of the table
- A detail endpoint, with three methods:
    - :code:`get(idx)`, that returns the entry with the given id
    - :code:`put(idx, **kwargs)`, that updates the entry with the given id with the given data
    - :code:`delete(idx)`, that deletes the entry with the given id

If one or several of those methods are not necessary, the option :code:`--remove_methods` allows to not
generate some of those methods. Note that the method :code:`post()` is the only one that can not be
removed.

Example:

.. code-block:: console

    python generate_from_schema C:/Users/User/instance.json application_name --remove_methods getOne deleteAll

In that example, for each table, the global endpoint will not contain the :code:`delete()` method and
the detail endpoint will not contain the :code:`get()` method. The choices for this method are
:code:`getOne`, :code:`getAll`, :code:`update`, :code:`deleteOne` and :code:`deleteAll`.

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

    python generate_from_schema C:/Users/User/instance.json application_name --one table_name

In that case, only one table will be created.

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
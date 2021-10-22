Write a json-schema
=======================

.. highlight:: json

Basics of schemas
------------------------------

The schemas are descriptions of the data accepted by the application.

In particular, a schema must describe a dictionary of tables, each table described as a list of dictionaries whose keys are the name of the columns.

Let's take an example of data with two tables ``customers`` and ``allowedTrailers``.

**customers**:

==========  ==========
IdCustomer  Demand
==========  ==========
1               4
2               5
3               7
==========  ==========

**allowedTrailers**:

==========  ==========
IdCustomer  idTrailer
==========  ==========
1               7
1               8
2               9
3               4
==========  ==========

The schema will look like this::

    { "$schema": "http://json-schema.org/schema#",
     "type": "object",
     "properties": {
       "customers": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "index": {
               "type": "integer"
             },
             "Demand": {
               "type": "integer"
             }
           },
           "required": [
             "index",
             "Demand"
           ]
         }
       },
       "allowedTrailers": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "idCustomer": {
               "type": "integer"
             },
             "idTrailer": {
               "type": "integer"
             }
           },
           "required": [
             "idCustomer",
             "idTrailer"
           ]
         }
       }
     },
     "required": [
       "customers",
       "allowedTrailers"
     ]
    }


This basically means that our input data should be an object containing two tables (``customers`` and ``allowedTrailers``) represented as arrays of objects.
It is important to note three things:

No nested list types
************************

If your data previously looked like this:

==========  ========== =================                                 
IdCustomer  Demand     idTrailer             
==========  ========== =================                                 
1               4      [7, 8]               
2               5      [9]                  
3               7      [4]                             
==========  ========== =================                                 

Then it should be converted into two tables like shown before. The cells of a table must only contain unidimensional values

Required property
********************

The property “required” must be included for all objects that are needed to solve the problem.

In real problems, pure data is usually complemented by auxiliary information (such as that used to display in screens: names, comments, coordinates, etc.). This information should not be included in the “required” property because it is not required to produce a solution for the problem (it is still useful to be defined so it can be validated by the schema).

Exception for “simple objects”
**********************************

Even though most properties of our schema object must be arrays, an exception is made for the parameters of the problems that are unidimensional and can not be represented as lists. For instance, if in our previous example we had two parameters ``trailersCapacity`` and ``timeHorizon``, we would add a property ``parameters`` to our schema::

    { "$schema": "http://json-schema.org/schema#",
     "type": "object",
     "properties": {
       "parameters": {
         "type": "object",
         "properties": {
           "trailersCapacity": {
             "type": "integer"
           },
           "timeHorizon": {
             "type": "integer"
           }
         },
         "required": ["trailersCapacity", "timeHorizon"]
       },
       "customers": {},
       "allowedTrailers": {}
       },
     "required": [
       "customers",
       "allowedTrailers",
       "parameters"
     ]
    }

Naming conventions
*********************

When naming columns in a "master table", we refer to the unique id of each row
as "id" (see the ``shifts`` property below. When an id is used as a foreign
key in another table (see the ``resources_not_available`` property), we use
"id_shift" to denote that is the id of the shift that we are using::

    {
    "$schema": "http://json-schema.org/schema#",
    "type": "object",
    "properties": {
        "shifts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "start_time": {
                        "type": "string"
                    },
                    "end_time": {
                        "type": "string"
                    }
                },
                "required": [
                    "id",
                    "start_time",
                    "end_time"
                ]
            }
        },
        "resources_unavailable": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id_resource": {
                        "type": "string"
                    },
                    "id_shift": {
                        "type": "string"
                    },
                    "start_date": {
                        "type": "string"
                    },
                    "end_date": {
                        "type": "string"
                    }
                },
                "required": [
                    "id_resource",
                    "id_shift",
                    "start_date",
                    "end_date"
                ]
            }
        },
        "required": ["shifts", "resources_unavailable"]
    }

As explained in the section beforehand, the parameters that are unidimensional should be on a table called ``parameters``.

Example with TSP
-------------------

Let's take the well known TSP problem and generate an instance, a solution and a configuration following these guidelines.

Instance schema
****************************

An instance of a TSP is a simple graph with positive weights in each arc. We will represent the graph by a list of arcs::

    {
        "$schema": "http://json-schema.org/schema#",
        "type": "object",
        "properties": {
            "arcs": {
                "description": "Arc information between pairs of nodes",
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "n1": {"type": "integer"},
                        "n2": {"type": "integer"},
                        "w": {"type": "float"}
                    },
                    "required": ["n1", "n2", "w"]
                }
            }
        },
        "required": ["arcs"]
    }


We are using ``n1`` and ``n2`` to call each the first and second node of each arc. We use ``w`` to call the weight of the arc.

Solution schema
****************************

A solution to a TSP, is the sequence in which nodes should be visited. We *could* use an ordered array of nodes. Nevertheless, we need to use an array of objects. We will also add a new property with the position of the node in the sequence.::

    {
        "$schema": "http://json-schema.org/schema#",
        "type": "object",
        "properties": {
            "route": {
                "description": "Order of nodes in each route",
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "node": {"type": "integer"},
                        "pos": {"type": "integer"}
                    },
                    "required": ["pos","node"]
                }
            }
        },
        "required": ["route"]
    }


``node`` represents each node in the sequence. ``pos`` represents the position of each node in the sequence.

An alternative, still valid, schema would be::

    {
        "$schema": "http://json-schema.org/schema#",
        "type": "object",
        "properties": {
            "route": {
                "description": "Order of nodes in each route",
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "node": {"type": "integer"},
                    },
                    "required": ["node"]
                }
            }
        },
        "required": ["route"]
    }


Here we assume the array is sorted and so we do not need the position of the node explicitly.


Configuration schema
*********************

The configuration will depend on the application. We usually have some default configuration tailored to MIP problems. Here is a minimalistic proposal::


    {
        "$schema": "http://json-schema.org/schema#",
        "type": "object",
        "properties": {
            "timeLimit": {"type": "float"},
            "seed": {"type": "integer"},
            "gap": {"type": "float"},
            "solver": {
                "type": "string",
                "enum": ["naive"],
                "default": "naive"
            }
        }
    }



``timeLimit`` constraints the time the solution method can run. ``gapRel`` provides a tolerance measured in relative gap (to the best possible solution). ``seed`` provides a way to make the solution method deterministic. The ``solver`` property is mandatory for all solution methods and should always have this format (a string with an "enum" attribute).

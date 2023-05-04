# Endpoints
SP8 = 8 * " "
SP12 = 12 * " "


class EndpointGenerator:
    def __init__(self, table_name, app_name, model_name, schemas_names):
        self.table_name = table_name
        self.app_name = app_name
        self.model_name = model_name
        self.schemas_names = schemas_names
        self.descriptions = {
            "base": "Endpoint used to manage the table",
            "bulk": "Endpoint used to perform bulk operations on the table",
            "detail": "Endpoint used to perform detail operations on the table"
        }

    def generate_endpoints_imports(self, roles):
        """
        Generate the import text for an endpoint.

        :param roles: list of roles to import
        :return: import text
        """
        return (
            "# Imports from libraries\n"
            "from flask_apispec import doc, marshal_with, use_kwargs\n\n"
            "# Import from internal modules\n"
            "from cornflow.endpoints.meta_resource import BaseMetaResource\n\n"
            f"from ..models import {self.model_name}\n"
            f"from ..schemas import {', '.join(self.schemas_names.values())}\n\n"
            "from cornflow.shared.authentication import authenticate, Auth\n"
            f"from cornflow.shared.const import {', '.join(roles)}\n"
        )

    def get_type_methods(self, methods, ep_type):
        """
        Select the methods of the table to use in the type of endpoint.

        :param methods: list of methods used for this table
        :param ep_type: type of endpoint (base, bulk or detail)
        :return:
        """
        name_types = dict(base="list", bulk ="bulk", detail ="detail")
        return [v[0] for v in [m.split("_") for m in methods] if v[1] == name_types[ep_type]]

    def generate_endpoint_description(self, methods, ep_type="base"):
        """
        Generate the description of an endpoint.

        :param methods: list of available methods.
        :param ep_type: type of endpoint (base, bulk or detail)

        :return: the description text
        """
        type_methods = self.get_type_methods(methods, ep_type)
        description = self.descriptions[ep_type]
        app_name = f' of app {self.app_name}' if self.app_name is not None else ""
        res = '    """\n'
        res += f"    {description} {self.table_name}{app_name}.\n\n"
        res += f"    Available methods: [{', '.join(type_methods)}]\n"
        res += '    """\n'
        return res

    def generate_endpoint_init(self):
        res = "    def __init__(self):\n"
        res += SP8 + "super().__init__()\n"
        res += SP8 + f"self.data_model = {self.model_name}\n"
        res += SP8 + f"self.unique = ['id']\n"
        return res

    def generate_endpoint_get_all(self):
        schema_name = self.schemas_names["one"]
        res = "    @doc(\n"
        res += SP8 + 'description="Get list of all the elements in the table",\n'
        res += SP8 + f'tags=["{self.app_name}"],\n'
        res += "    )\n"
        res += "    @authenticate(auth_class=Auth())\n"
        res += f"    @marshal_with({schema_name}(many=True))\n"
        res += "    def get(self, **kwargs):\n"
        res += SP8 + '"""\n'
        res += SP8 + "API method to get all the rows of the table.\n"
        res += (
            SP8
            + "It requires authentication to be passed in the form of a token that has to be linked to\n"
        )
        res += SP8 + "an existing session (login) made by a user.\n\n"
        res += (
            SP8
            + ":return: A list of objects with the data, and an integer with the HTTP status code.\n"
        )
        res += SP8 + ":rtype: Tuple(dict, integer)\n"
        res += SP8 + '"""\n'
        res += SP8 + "return self.get_list(**kwargs)\n"
        return res

    def generate_endpoint_get_one(self):
        schema_name = self.schemas_names["one"]
        res = "    @doc(\n"
        res += SP8 + 'description="Get one element of the table",\n'
        res += SP8 + f'tags=["{self.app_name}"],\n'
        res += "    )\n"
        res += "    @authenticate(auth_class=Auth())\n"
        res += f"    @marshal_with({schema_name})\n"
        res += "    def get(self, idx):\n"
        res += SP8 + '"""\n'
        res += SP8 + "API method to get a row of the table.\n"
        res += (
            SP8
            + "It requires authentication to be passed in the form of a token that has to be linked to\n"
        )
        res += SP8 + "an existing session (login) made by a user.\n\n"
        res += SP8 + ":param idx: ID of the row\n"
        res += (
            SP8
            + ":return: A dictionary with the response data and an integer with the HTTP status code.\n"
        )
        res += SP8 + ":rtype: Tuple(dict, integer)\n"
        res += SP8 + '"""\n'
        res += SP8 + "return self.get_detail(idx=idx)\n"
        return res

    def generate_endpoint_post(self):
        schema_marshal = self.schemas_names["one"]
        schema_kwargs = self.schemas_names["postRequest"]
        res = "    @doc(\n"
        res += SP8 + 'description="Add a new row to the table",\n'
        res += SP8 + f'tags=["{self.app_name}"],\n'
        res += "    )\n"
        res += "    @authenticate(auth_class=Auth())\n"
        res += f"    @marshal_with({schema_marshal})\n"
        res += f'    @use_kwargs({schema_kwargs}, location="json")\n'
        res += "    def post(self, **kwargs):\n"
        res += SP8 + '"""\n'
        res += SP8 + "API method to add a row to the table.\n"
        res += (
            SP8
            + "It requires authentication to be passed in the form of a token that has to be linked to\n"
        )
        res += SP8 + "an existing session (login) made by a user.\n\n"
        res += SP8 + ":return: An object with the data for the created row,\n"
        res += SP8 + "and an integer with the HTTP status code.\n"
        res += SP8 + ":rtype: Tuple(dict, integer)\n"
        res += SP8 + '"""\n'
        res += SP8 + "return self.post_list(data=kwargs)\n"
        return res

    def generate_endpoint_delete_one(self):
        res = "    @doc(\n"
        res += SP8 + 'description="Delete one row of the table",\n'
        res += SP8 + f'tags=["{self.app_name}"], \n'
        res += "    )\n"
        res += "    @authenticate(auth_class=Auth())\n"
        res += "    def delete(self, idx):\n"
        res += SP8 + '"""\n'
        res += SP8 + "API method to delete a row of the table.\n"
        res += (
            SP8
            + "It requires authentication to be passed in the form of a token that has to be linked to\n"
        )
        res += SP8 + "an existing session (login) made by a user.\n\n"
        res += SP8 + ":param idx: ID of the row\n"
        res += (
            SP8
            + ":return: A dictionary with a message (error if authentication failed, "
            + "or the execution does not exist or\n"
        )
        res += SP8 + "a message) and an integer with the HTTP status code.\n"
        res += SP8 + ":rtype: Tuple(dict, integer)\n"
        res += SP8 + '"""\n'
        res += SP8 + "return self.delete_detail(idx=idx)\n"
        return res

    def generate_endpoint_put(self):
        schema_name = self.schemas_names["editRequest"]
        res = "    @doc(\n"
        res += SP8 + 'description="Edit one row of the table",\n'
        res += SP8 + f'tags=["{self.app_name}"], \n'
        res += "    )\n"
        res += "    @authenticate(auth_class=Auth())\n"
        res += f'    @use_kwargs({schema_name}, location="json")\n'
        res += "    def put(self, idx, **data):\n"
        res += SP8 + '"""\n'
        res += SP8 + "API method to edit a row of the table.\n"
        res += (
            SP8
            + "It requires authentication to be passed in the form of a token that has to be linked to\n"
        )
        res += SP8 + "an existing session (login) made by a user.\n\n"
        res += SP8 + ":param idx: ID of the row\n"
        res += (
            SP8
            + ":return: A dictionary with a message (error if authentication failed, "
            + "or the execution does not exist or\n"
        )
        res += SP8 + "a message) and an integer with the HTTP status code.\n"
        res += SP8 + ":rtype: Tuple(dict, integer)\n"
        res += SP8 + '"""\n'
        res += SP8 + "return self.put_detail(data=data, idx=idx)\n"
        return res

    def generate_endpoint_patch(self):
        schema_name = self.schemas_names["editRequest"]
        res = "    @doc(\n"
        res += SP8 + 'description="Patch one row of the table",\n'
        res += SP8 + f'tags=["{self.app_name}"], \n'
        res += "    )\n"
        res += "    @authenticate(auth_class=Auth())\n"
        res += f'    @use_kwargs({schema_name}, location="json")\n'
        res += "    def patch(self, idx, **data):\n"
        res += SP8 + '"""\n'
        res += SP8 + "API method to patch a row of the table.\n"
        res += (
            SP8
            + "It requires authentication to be passed in the form of a token that has to be linked to\n"
        )
        res += SP8 + "an existing session (login) made by a user.\n\n"
        res += SP8 + ":param idx: ID of the row\n"
        res += (
            SP8
            + ":return: A dictionary with a message (error if authentication failed, "
            + "or the execution does not exist or\n"
        )
        res += SP8 + "a message) and an integer with the HTTP status code.\n"
        res += SP8 + ":rtype: Tuple(dict, integer)\n"
        res += SP8 + '"""\n'
        res += SP8 + "return self.patch_detail(data=data, idx=idx)\n"
        return res

    def generate_endpoint_post_bulk(self):
        schema_marshal = self.schemas_names["one"]
        schema_kwargs = self.schemas_names["postBulkRequest"]
        res = "    @doc(\n"
        res += SP8 + 'description="Add several new rows to the table",\n'
        res += SP8 + f'tags=["{self.app_name}"],\n'
        res += "    )\n"
        res += "    @authenticate(auth_class=Auth())\n"
        res += f"    @marshal_with({schema_marshal}(many=True))\n"
        res += f'    @use_kwargs({schema_kwargs}, location="json")\n'
        res += "    def post(self, **kwargs):\n"
        res += SP8 + '"""\n'
        res += SP8 + "API method to add several new rows to the table.\n"
        res += (
            SP8
            + "It requires authentication to be passed in the form of a token that has to be linked to\n"
        )
        res += SP8 + "an existing session (login) made by a user.\n\n"
        res += SP8 + ":return: An object with the data for the created row,\n"
        res += SP8 + "and an integer with the HTTP status code.\n"
        res += SP8 + ":rtype: Tuple(dict, integer)\n"
        res += SP8 + '"""\n'
        res += SP8 + "return self.post_bulk(data=kwargs)\n"
        return res

    def generate_endpoint_put_bulk(self):
        schema_marshal = self.schemas_names["one"]
        schema_kwargs = self.schemas_names["putBulkRequest"]
        res = "    @doc(\n"
        res += SP8 + 'description="Updates several rows of the table or adds them if they do not exist",\n'
        res += SP8 + f'tags=["{self.app_name}"],\n'
        res += "    )\n"
        res += "    @authenticate(auth_class=Auth())\n"
        res += f"    @marshal_with({schema_marshal}(many=True))\n"
        res += f'    @use_kwargs({schema_kwargs}, location="json")\n'
        res += "    def put(self, **kwargs):\n"
        res += SP8 + '"""\n'
        res += SP8 + "API method to add several new rows to the table.\n"
        res += (
            SP8
            + "It requires authentication to be passed in the form of a token that has to be linked to\n"
        )
        res += SP8 + "an existing session (login) made by a user.\n\n"
        res += SP8 + ":return: An object with the data for the created row,\n"
        res += SP8 + "and an integer with the HTTP status code.\n"
        res += SP8 + ":rtype: Tuple(dict, integer)\n"
        res += SP8 + '"""\n'
        res += SP8 + "return self.post_bulk_update(data=kwargs)\n"
        return res

    def generate_endpoint(self, method):
        ep_map = dict(get_list=self.generate_endpoint_get_all, post_list=self.generate_endpoint_post, get_detail=self.generate_endpoint_get_one,
                      put_detail=self.generate_endpoint_put,
                      patch_detail=self.generate_endpoint_patch,
                      delete_detail= self.generate_endpoint_delete_one,
                      post_bulk=self.generate_endpoint_post_bulk,
                      put_bulk=self.generate_endpoint_put_bulk
        )
        return ep_map[method]()

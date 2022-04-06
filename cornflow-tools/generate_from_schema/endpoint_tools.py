# Endpoints
SP8 = 8 * ' '
SP12 = 12 * ' '


class EndpointGenerator:
    def __init__(self, table_name, app_name, model_name, schemas_names):
        self.table_name = table_name
        self.app_name = app_name
        self.model_name = model_name
        self.schemas_names = schemas_names

    def generate_endpoints_imports(self):
        return "# Imports from libraries\n" \
              "from flask_apispec import doc, marshal_with, use_kwargs\n" \
              "from flask_apispec.views import MethodResource\n\n" \
              "# Import from internal modules\n" \
              "from .meta_resource import MetaResource\n" \
              "from ..shared.const import SERVICE_ROLE\n" \
              "from ..shared.authentification import Auth\n" \
              f"from ..models import {self.model_name}\n" \
              f"from ..schemas import {', '.join(self.schemas_names.values())}\n\n"

    def generate_endpoint_description(self):
        res = '    """\n'
        res += f'    Endpoint used to manage the table {self.table_name} of app {self.app_name}\n'
        res += '    """\n'
        return res

    def generate_endpoint_init(self):
        res = '    def __init__(self):\n'
        res += SP8 + 'super().__init__()\n'
        res += SP8 + f'self.model = {self.model_name}\n'
        res += SP8 + f'self.query = {self.model_name}.get_one_object\n'
        res += SP8 + f'self.primary_key = "id"\n'
        return res

    def generate_endpoint_get_all(self):
        schema_name = self.schemas_names['one']
        res = '    @doc(\n'
        res += SP8 + 'description="Get list of all the elements in the table",\n'
        res += SP8 + f'tags=["{self.app_name}"],\n'
        res += '    )\n'
        res += '    @Auth.auth_required\n'
        res += f'    @marshal_with({schema_name}(many=True))\n'
        res += '    def get(self):\n'
        res += SP8 + '"""\n'
        res += SP8 + 'API method to get all the rows of the table.\n'
        res += SP8 + 'It requires authentication to be passed in the form of a token that has to be linked to\n'
        res += SP8 + 'an existing session (login) made by a user.\n\n'
        res += SP8 + ':return: A list of objects with the data, and an integer with the HTTP status code.\n'
        res += SP8 + ':rtype: Tuple(dict, integer)\n'
        res += SP8 + '"""\n'
        res += SP8 + 'return self.model.get_all_objects()\n'
        return res

    def generate_endpoint_get_one(self):
        schema_name = self.schemas_names['one']
        res = '    @doc(\n'
        res += SP8 + 'description="Get one element of the table",\n'
        res += SP8 + f'tags=["{self.app_name}"],\n'
        res += '    )\n'
        res += '    @Auth.auth_required\n'
        res += f'    @marshal_with({schema_name})\n'
        res += '    def get(self, idx):\n'
        res += SP8 + '"""\n'
        res += SP8 + 'API method to get a row of the table.\n'
        res += SP8 + 'It requires authentication to be passed in the form of a token that has to be linked to\n'
        res += SP8 + 'an existing session (login) made by a user.\n\n'
        res += SP8 + ':param idx: ID of the row\n'
        res += SP8 + ':return: A dictionary with the response data and an integer with the HTTP status code.\n'
        res += SP8 + ':rtype: Tuple(dict, integer)\n'
        res += SP8 + '"""\n'
        res += SP8 + 'return self.model.get_one_object(idx)\n'
        return res

    def generate_endpoint_post(self):
        schema_marshal = self.schemas_names['one']
        schema_kwargs = self.schemas_names['postRequest']
        res = '    @doc(\n'
        res += SP8 + 'description="Add a new row to the table",\n'
        res += SP8 + f'tags=["{self.app_name}"],\n'
        res += '    )\n'
        res += '    @Auth.auth_required\n'
        res += f'    @marshal_with({schema_marshal})\n'
        res += f'    @use_kwargs({schema_kwargs}, location="json")\n'
        res += '    def post(self, **kwargs):\n'
        res += SP8 + '"""\n'
        res += SP8 + 'API method to add a row to the table.\n'
        res += SP8 + 'It requires authentication to be passed in the form of a token that has to be linked to\n'
        res += SP8 + 'an existing session (login) made by a user.\n\n'
        res += SP8 + ':return: An object with the data for the created row,\n'
        res += SP8 + 'and an integer with the HTTP status code.\n'
        res += SP8 + ':rtype: Tuple(dict, integer)\n'
        res += SP8 + '"""\n'
        res += SP8 + 'response = self.post_list(kwargs)\n'
        res += SP8 + 'return response\n'
        return res

    def generate_endpoint_delete_all(self):
        res = '    @doc(\n'
        res += SP8 + 'description="Delete all the data of the table",\n'
        res += SP8 + f'tags=["{self.app_name}"],\n'
        res += '    )\n'
        res += '    @Auth.auth_required\n'
        res += '    def delete(self):\n'
        res += SP8 + '"""\n'
        res += SP8 + 'API method to delete all the rows of the table.\n'
        res += SP8 + 'It requires authentication to be passed in the form of a token that has to be linked to\n'
        res += SP8 + 'an existing session (login) made by a user.\n\n'
        res += SP8 + ':return: A dictionary with a message (error if authentication failed, or the execution does not exist or\n'
        res += SP8 + 'a message) and an integer with the HTTP status code.\n'
        res += SP8 + ':rtype: Tuple(dict, integer)\n'
        res += SP8 + '"""\n'
        res += SP8 + 'items = self.model.get_all_objects()\n'
        res += SP8 + 'for item in items:\n'
        res += SP12 + 'item.disable()\n'
        res += SP8 + 'return {"message": "All the objects have been deleted"}, 200\n'
        return res

    def generate_endpoint_delete_one(self):
        res = '    @doc(\n'
        res += SP8 + 'description="Delete one row of the table",\n'
        res += SP8 + f'tags=["{self.app_name}"], \n'
        res += '    )\n'
        res += '    @Auth.auth_required\n'
        res += '    def delete(self, idx):\n'
        res += SP8 + '"""\n'
        res += SP8 + 'API method to delete a row of the table.\n'
        res += SP8 + 'It requires authentication to be passed in the form of a token that has to be linked to\n'
        res += SP8 + 'an existing session (login) made by a user.\n\n'
        res += SP8 + ':param idx: ID of the row\n'
        res += SP8 + ':return: A dictionary with a message (error if authentication failed, or the execution does not exist or\n'
        res += SP8 + 'a message) and an integer with the HTTP status code.\n'
        res += SP8 + ':rtype: Tuple(dict, integer)\n'
        res += SP8 + '"""\n'
        res += SP8 + 'response = self.delete_detail(idx)\n'
        res += SP8 + 'return response\n'
        return res

    def generate_endpoint_put(self):
        schema_name = self.schemas_names['editRequest']
        res = '    @doc(\n'
        res += SP8 + 'description="Edit one row of the table",\n'
        res += SP8 + f'tags=["{self.app_name}"], \n'
        res += '    )\n'
        res += '    @Auth.auth_required\n'
        res += f'    @use_kwargs({schema_name}, location="json")\n'
        res += '    def put(self, idx, **data):\n'
        res += SP8 + '"""\n'
        res += SP8 + 'API method to edit a row of the table.\n'
        res += SP8 + 'It requires authentication to be passed in the form of a token that has to be linked to\n'
        res += SP8 + 'an existing session (login) made by a user.\n\n'
        res += SP8 + ':param idx: ID of the row\n'
        res += SP8 + ':return: A dictionary with a message (error if authentication failed, or the execution does not exist or\n'
        res += SP8 + 'a message) and an integer with the HTTP status code.\n'
        res += SP8 + ':rtype: Tuple(dict, integer)\n'
        res += SP8 + '"""\n'
        res += SP8 + 'response = self.put_detail(data, idx)\n'
        res += SP8 + 'return response\n'
        return res

# Endpoints
SP8 = 8 * " "
SP12 = 12 * " "

DOC_DECORATOR = "@doc"
AUTH_DECORATOR = "@authenticate(auth_class=Auth())"
COMMENT_AUTH_1 = "It requires authentication to be passed in the form of a token that has to be linked to\n"
COMMENT_AUTH_2 = "an existing session (login) made by a user.\n"
PARAM_IDX_DOCSTRING = ":param idx: ID of the row\n"
RETURN_DOCSTRING_1 = ":rtype: Tuple(dict, integer)\n"


# TODO: refactor these methods to make them more modular
class EndpointGenerator:
    def __init__(self, table_name, app_name, model_name, schemas_names):
        self.table_name = table_name
        self.app_name = app_name
        self.model_name = model_name
        self.schemas_names = schemas_names
        self.descriptions = {
            "base": "Endpoint used to manage the table",
            "bulk": "Endpoint used to perform bulk operations on the table",
            "detail": "Endpoint used to perform detail operations on the table",
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
        name_types = dict(base="list", bulk="bulk", detail="detail")
        return [
            v[0] for v in [m.split("_") for m in methods] if v[1] == name_types[ep_type]
        ]

    def generate_endpoint_description(self, methods, ep_type="base"):
        """
        Generate the description of an endpoint.

        :param methods: list of available methods.
        :param ep_type: type of endpoint (base, bulk or detail)

        :return: the description text
        """
        type_methods = self.get_type_methods(methods, ep_type)
        description = self.descriptions[ep_type]
        app_name = f" of app {self.app_name}" if self.app_name is not None else ""
        res = '    """\n'
        res += f"    {description} {self.table_name}{app_name}.\n\n"
        res += f"    Available methods: [{', '.join(type_methods)}]\n"
        res += '    """\n'
        return res

    def generate_endpoint_init(self):
        res = "    def __init__(self):\n"
        res += SP8 + "super().__init__()\n"
        res += SP8 + f"self.data_model = {self.model_name}\n"
        res += SP8 + "self.unique = ['id']\n"
        return res

    def _generate_docstring(self, summary, param_idx=False, return_desc=""):
        """Generates the common docstring structure for endpoint methods."""
        lines = [
            SP8 + '"""\n',
            SP8 + summary + "\n",
            f"{SP8}{COMMENT_AUTH_1}",
            f"{SP8}{COMMENT_AUTH_2}",
        ]
        if param_idx:
            lines.append(f"{SP8}{PARAM_IDX_DOCSTRING}")
        if return_desc:
            lines.append(SP8 + return_desc + "\n")
        lines.append(f"{SP8}{RETURN_DOCSTRING_1}")
        lines.append(SP8 + '"""\n')
        return "".join(lines)

    def _generate_method(
        self,
        http_method: str,
        method_name: str,
        is_detail: bool,
        doc_description: str,
        docstring_summary: str,
        docstring_return_desc: str,
        base_method_call: str,
        marshal_schema: str = None,
        kwargs_schema: str = None,
        marshal_many: bool = False,
    ):
        """Generates the complete string for an endpoint method."""
        lines = []

        # @doc decorator
        lines.append(f"    {DOC_DECORATOR}(")
        lines.append(f'        description="{doc_description}",')
        lines.append(
            f'        tags=["{self.app_name}"],'
        )  # Add comma if needed for future args
        lines.append("    )")

        # @authenticate decorator
        lines.append(f"    {AUTH_DECORATOR}")

        # @marshal_with decorator
        if marshal_schema:
            many_str = "(many=True)" if marshal_many else ""
            lines.append(f"    @marshal_with({marshal_schema}{many_str})")

        # @use_kwargs decorator
        if kwargs_schema:
            lines.append(f'    @use_kwargs({kwargs_schema}, location="json")')

        # Method signature
        params = "idx" if is_detail else "**kwargs"
        if http_method in ["put", "patch"] and is_detail:
            params = "idx, **data"
        elif http_method == "post" and not is_detail:
            params = "**kwargs"  # Keep as kwargs for bulk post

        lines.append(f"    def {method_name}(self, {params}):")

        # Docstring
        docstring = self._generate_docstring(
            summary=docstring_summary,
            param_idx=is_detail,
            return_desc=docstring_return_desc,
        )
        lines.append(docstring.strip("\n"))  # Remove leading/trailing newlines if any

        # Base method call
        lines.append(f"{SP8}return {base_method_call}")

        return "\n".join(lines) + "\n"  # Ensure trailing newline

    def generate_endpoint_get_all(self):
        return self._generate_method(
            http_method="get",
            method_name="get",
            is_detail=False,
            doc_description="Get list of all the elements in the table",
            marshal_schema=self.schemas_names["one"],
            marshal_many=True,
            docstring_summary="API method to get all the rows of the table.",
            docstring_return_desc=":return: A list of objects with the data, and an integer with the HTTP status code.",
            base_method_call="self.get_list(**kwargs)",
        )

    def generate_endpoint_get_one(self):
        return self._generate_method(
            http_method="get",
            method_name="get",
            is_detail=True,
            doc_description="Get one element of the table",
            marshal_schema=self.schemas_names["one"],
            docstring_summary="API method to get a row of the table.",
            docstring_return_desc=":return: A dictionary with the response data and an integer with the HTTP status code.",
            base_method_call="self.get_detail(idx=idx)",
        )

    def generate_endpoint_post(self):
        return self._generate_method(
            http_method="post",
            method_name="post",
            is_detail=False,
            doc_description="Add a new row to the table",
            marshal_schema=self.schemas_names["one"],
            kwargs_schema=self.schemas_names["postRequest"],
            docstring_summary="API method to add a row to the table.",
            docstring_return_desc=":return: An object with the data for the created row,\\n"
            + SP8
            + "and an integer with the HTTP status code.",
            base_method_call="self.post_list(data=kwargs)",
        )

    def generate_endpoint_delete_one(self):
        return self._generate_method(
            http_method="delete",
            method_name="delete",
            is_detail=True,
            doc_description="Delete one row of the table",
            docstring_summary="API method to delete a row of the table.",
            docstring_return_desc=":return: A dictionary with a message (error if authentication failed, or the execution does not exist or\\n"
            + SP8
            + "a message) and an integer with the HTTP status code.",
            base_method_call="self.delete_detail(idx=idx)",
        )

    def generate_endpoint_put(self):
        return self._generate_method(
            http_method="put",
            method_name="put",
            is_detail=True,
            doc_description="Edit one row of the table",
            kwargs_schema=self.schemas_names["editRequest"],
            docstring_summary="API method to edit a row of the table.",
            docstring_return_desc=":return: A dictionary with a message (error if authentication failed, or the execution does not exist or\\n"
            + SP8
            + "a message) and an integer with the HTTP status code.",
            base_method_call="self.put_detail(data=data, idx=idx)",
        )

    def generate_endpoint_patch(self):
        return self._generate_method(
            http_method="patch",
            method_name="patch",
            is_detail=True,
            doc_description="Patch one row of the table",
            kwargs_schema=self.schemas_names["editRequest"],
            docstring_summary="API method to patch a row of the table.",
            docstring_return_desc=":return: A dictionary with a message (error if authentication failed, or the execution does not exist or\\n"
            + SP8
            + "a message) and an integer with the HTTP status code.",
            base_method_call="self.patch_detail(data=data, idx=idx)",
        )

    def generate_endpoint_post_bulk(self):
        return self._generate_method(
            http_method="post",
            method_name="post",
            is_detail=False,
            doc_description="Add several new rows to the table",
            marshal_schema=self.schemas_names["one"],
            marshal_many=True,
            kwargs_schema=self.schemas_names["postBulkRequest"],
            docstring_summary="API method to add several new rows to the table.",
            docstring_return_desc=":return: An object with the data for the created row,\\n"
            + SP8
            + "and an integer with the HTTP status code.",
            base_method_call="self.post_bulk(data=kwargs)",
        )

    def generate_endpoint_put_bulk(self):
        return self._generate_method(
            http_method="put",
            method_name="put",
            is_detail=False,
            doc_description="Updates several rows of the table or adds them if they do not exist",
            marshal_schema=self.schemas_names["one"],
            marshal_many=True,
            kwargs_schema=self.schemas_names["putBulkRequest"],
            docstring_summary="API method to add or update several rows to the table.",
            docstring_return_desc=":return: An object with the data for the created/updated rows,\\n"
            + SP8
            + "and an integer with the HTTP status code.",
            base_method_call="self.post_bulk_update(data=kwargs)",
        )

    def generate_endpoint(self, method):
        ep_map = dict(
            get_list=self.generate_endpoint_get_all,
            post_list=self.generate_endpoint_post,
            get_detail=self.generate_endpoint_get_one,
            put_detail=self.generate_endpoint_put,
            patch_detail=self.generate_endpoint_patch,
            delete_detail=self.generate_endpoint_delete_one,
            post_bulk=self.generate_endpoint_post_bulk,
            put_bulk=self.generate_endpoint_put_bulk,
        )
        generator_func = ep_map.get(method)
        if generator_func is None:
            raise ValueError(f"Unsupported endpoint generation method: {method}")
        return generator_func()

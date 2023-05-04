# Import from libraries
from flask_apispec import doc, use_kwargs
from flask import current_app

# Import from internal modules
from cornflow.endpoints.meta_resource import BaseMetaResource
from cornflow.schemas.common import QueryFilters
from cornflow.shared.authentication import Auth, authenticate
from cornflow.shared.const import SERVICE_ROLE
from cornflow.shared.exceptions import InvalidUsage, ObjectDoesNotExist
from cornflow.shared.utils_tables import get_all_tables, item_as_dict, items_as_dict_list


class TablesEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = None
        self.tables = get_all_tables()

    @doc(description="Get all rows of a table", tags=["Tables"])
    @authenticate(auth_class=Auth())
    @use_kwargs(QueryFilters, location="query")
    def get(self, table_name, **kwargs):
        """
        API (GET) method to get all directory structure of cases for the user
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a tree structure of the cases and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        self.data_model = self.tables[table_name]["model"]
        current_app.logger.info(
            f"User {self.get_user()} gets all rows of table {table_name}."
        )
        res = self.get_list(user=self.get_user(), **kwargs)
        return items_as_dict_list(res), 200


class TablesDetailsEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = None
        self.tables = get_all_tables()

    @doc(description="Get a row", tags=["Tables"])
    @authenticate(auth_class=Auth())
    @BaseMetaResource.get_data_or_404
    def get(self, table_name, idx):
        """
        :param table_name: Name of the table to get data from
        :param idx: id of the row.
        :return:
        :rtype: Tuple(dict, integer)
        """
        model_info = self.tables[table_name]
        self.data_model = model_info["model"]
        conv_idx = idx
        if model_info["convert_id"]:
            try:
                conv_idx = int(idx)
            except (ValueError, TypeError):
                raise InvalidUsage(
                    "Invalid identifier.",
                    log_txt=f"Error while user {self.get_user()} tries to access row {idx} of table {table_name}. "
                    f"Identifier is not valid.",
                )

        current_app.logger.info(
            f"User {self.get_user()} gets row {idx} of table {table_name}."
        )
        res = self.get_detail(idx=conv_idx)
        if res is None:
            raise ObjectDoesNotExist(
                log_txt=f"Error while user {self.get_user()} tries to access row {idx} of table {table_name}. "
                "The object does not exist."
            )
        return item_as_dict(res), 200
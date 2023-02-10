# Import from libraries
from cornflow_core.authentication import authenticate
from cornflow_core.exceptions import InvalidUsage, ObjectDoesNotExist, InvalidData
from cornflow_core.resources import BaseMetaResource
from sqlalchemy.exc import IntegrityError
from flask_apispec import doc, use_kwargs
from flask import current_app
import os

# Import from internal modules
from ..shared.const import SERVICE_ROLE
from ..shared.authentication import Auth
from ..shared.utils import get_all_tables, item_as_dict, items_as_dict_list
from ..schemas.tables import TableSchema


models_paths = [
    os.path.join(os.path.dirname(__file__), "..", ".."),
]


class TablesEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = None
        self.tables = get_all_tables(models_paths)

    @doc(description="Get all rows of a table", tags=["Tables"])
    @authenticate(auth_class=Auth())
    def get(self, table_name):
        """
        API (GET) method to get all directory structure of cases for the user
        It requires authentication to be passed in the form of a token that has to be linked to
        an existing session (login) made by a user

        :return: a dictionary with a tree structure of the cases and an integer with the HTTP status code
        :rtype: Tuple(dict, integer)
        """
        self.data_model = self.tables[table_name]["model"]
        current_app.logger.info(f"User {self.get_user()} gets all rows of table {table_name}.")
        res = self.data_model.query.all()
        return items_as_dict_list(res), 200

    @doc(description="Add a new row to the table", tags=["Tables"])
    @authenticate(auth_class=Auth())
    @use_kwargs(TableSchema, location="json")
    def post(self, table_name, **kwargs):
        """ """
        self.data_model = self.tables[table_name]["model"]
        current_app.logger.info(f"User {self.get_user()} adds a new row to the table {table_name}")
        try:
            res = self.post_list(data=kwargs["data"])
            return item_as_dict(res[0]), res[1]
        except IntegrityError as e:
            raise InvalidData(
                f"The data provided is not valid: {e}",
                log_txt=f"Error while user {self.get_user()} tries to add row to table {table_name}. "
                        f"The data provided is not valid: {e}"
            )


class TablesDetailsEndpoint(BaseMetaResource):
    ROLES_WITH_ACCESS = [SERVICE_ROLE]

    def __init__(self):
        super().__init__()
        self.data_model = None
        self.tables = get_all_tables(models_paths)

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
                    log_txt=f"Error while user {self.get_user()} tries to delete row {idx} of table {table_name}. "
                            f"Identifier is not valid."
                )

        current_app.logger.info(f"User {self.get_user()} gets row {idx} of table {table_name}.")
        res = self.get_detail(idx=conv_idx)
        if res is None:
            raise ObjectDoesNotExist(
                log_txt=f"Error while user {self.get_user()} tries to delete row {idx} of table {table_name}. "
                        "The object does not exist."
            )
        return item_as_dict(res), 200

    @doc(description="Edit a row from a table", tags=["Tables"])
    @authenticate(auth_class=Auth())
    @use_kwargs(TableSchema, location="json")
    def put(self, table_name, idx, **data):
        model_info = self.tables[table_name]
        self.data_model = model_info["model"]
        conv_idx = idx
        if model_info["convert_id"]:
            try:
                conv_idx = int(idx)
            except (ValueError, TypeError):
                raise InvalidUsage(
                    "Invalid identifier.",
                    log_txt=f"Error while user {self.get_user()} tries to delete row {idx} of table {table_name}. "
                            f"Identifier is not valid."
                )
        current_app.logger.info(f"Row {conv_idx} of table {table_name} was edited by user {self.get_user()}.")
        return self.put_detail(data=data["data"], idx=conv_idx, track_user=False)

    @doc(description="Delete a row", tags=["Users"])
    @authenticate(auth_class=Auth())
    def delete(self, table_name, idx):
        """
        :param table_name: Name of the table
        :param idx: id of the row
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
                    log_txt=f"Error while user {self.get_user()} tries to delete row {idx} of table {table_name}. "
                            f"Identifier is not valid."
                )
        current_app.logger.info(f"Row {conv_idx} of table {table_name} was deleted by user {self.get_user()}.")
        return self.delete_detail(idx=conv_idx)






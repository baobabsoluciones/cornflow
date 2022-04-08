from flask_apispec import marshal_with, use_kwargs
from flask_restful import Resource
from cornflow_core.authentication import BaseAuth
from cornflow_core.schemas import QueryFilters


class BaseMetaResource(Resource):

    DESCRIPTION = ""
    ROLES_WITH_ACCESS = []

    def __init__(self):
        super().__init__()
        self.data_model = None
        pass

    @use_kwargs(QueryFilters, location="query")
    def get_list(self, **kwargs):
        return self.data_model.get_all_objects(**kwargs), 200

    def get_detail(self):
        pass

    def post_list(self):
        pass

    def put_detail(self):
        pass

    def patch_detail(self):
        pass

    def delete_detail(self):
        pass

    def disable_detail(self):
        pass

    def activate_detail(self):
        pass

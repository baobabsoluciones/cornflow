from flask_apispec import marshal_with, use_kwargs
from flask_restful import Resource
from cornflow_core.authentication import Auth
from cornflow_core.schemas import QueryFilters


class BaseMetaResource(Resource):

    DESCRIPTION = ""
    ROLES_WITH_ACCESS = []
    AUTH_REQUIRED = True
    AUTH_CLASS = Auth

    def __init__(self):
        super().__init__()
        self.data_model = None
        pass

    @AUTH_CLASS.auth_decorator(auth=AUTH_REQUIRED)
    @use_kwargs(QueryFilters, location="query")
    def get_list(self, **kwargs):
        print(self.__class__)
        print(self.AUTH_CLASS)
        return self.data_model.get_all_objects(**kwargs), 200

    @Auth.auth_decorator(auth=AUTH_REQUIRED)
    def get_detail(self):
        pass

    @Auth.auth_decorator(auth=AUTH_REQUIRED)
    def post_list(self):
        pass

    @Auth.auth_decorator(auth=AUTH_REQUIRED)
    def put_detail(self):
        pass

    @Auth.auth_decorator(auth=AUTH_REQUIRED)
    def patch_detail(self):
        pass

    @Auth.auth_decorator(auth=AUTH_REQUIRED)
    def delete_detail(self):
        pass

    @Auth.auth_decorator(auth=AUTH_REQUIRED)
    def disable_detail(self):
        pass

    @Auth.auth_decorator(auth=AUTH_REQUIRED)
    def activate_detail(self):
        pass

from flask_restful import Resource
from flask import g

from cornflow_core.exceptions import InvalidUsage, ObjectDoesNotExist, NoPermission


class BaseMetaResource(Resource):

    DESCRIPTION = ""
    ROLES_WITH_ACCESS = []

    def __init__(self):
        super().__init__()
        self.data_model = None
        self.user = None
        self.foreign_data = None
        pass

    """
    METHODS USED FOR THE BASIC CRUD OPERATIONS: GET, POST, PUT, PATCH, DELETE 
    """

    def get_list(self, **kwargs):
        return self.data_model.get_all_objects(**kwargs)

    def get_detail(self, idx, **kwargs):
        return self.data_model.get_one_object(idx, **kwargs)

    def post_list(self, data, trace_field="user_id"):
        data = dict(data)
        data[trace_field] = self.get_user()
        item = self.data_model(data)
        if self.foreign_data is not None:
            for fk in self.foreign_data:
                owner = self.foreign_data[fk].query.get(getattr(item, fk))
                if owner is None:
                    raise ObjectDoesNotExist()
                if self.user != owner.user_id:
                    raise NoPermission()
        item.save()
        return item, 201

    def put_detail(self):
        pass

    def patch_detail(self):
        pass

    def delete_detail(self):
        pass

    """
    METHODS USED FOR ACTIVATING / DISABLING RECORDS IN CASE WE DO NOT WANT TO DELETE THEM STRAIGHT AWAY
    """

    def disable_detail(self):
        pass

    def activate_detail(self):
        pass

    """
    AUXILIAR METHODS
    """

    def get_user(self):
        if self.user is None:
            self.user = g.user["id"]
            if self.user is None:
                raise InvalidUsage("Error authenticating the user")
        return self.user

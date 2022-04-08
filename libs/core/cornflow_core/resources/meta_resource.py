from functools import wraps

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
        self.auth_class = None
        self.dependents = None
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

    def put_detail(self, data, **kwargs):
        item = self.data_model.get_one_object(**kwargs)
        if item is None:
            raise ObjectDoesNotExist("The data entity does not exist on the database")
        data = dict(data)
        data["user_id"] = self.get_user_id()
        item.update(data)
        return {"message": "Updated correctly"}, 200

    def patch_detail(self):
        pass

    def delete_detail(self, **kwargs):
        item = self.data_model.get_one_object(**kwargs)
        if item is None:
            raise ObjectDoesNotExist("The data entity does not exist on the database")
        if self.dependents is not None:
            for element in getattr(item, self.dependents):
                element.delete()
        item.delete()

        return {"message": "The object has been deleted"}, 200

    """
    METHODS USED FOR ACTIVATING / DISABLING RECORDS IN CASE WE DO NOT WANT TO DELETE THEM STRAIGHT AWAY
    """

    def disable_detail(self):
        pass

    def activate_detail(self):
        pass

    """
    AUXILIARY METHODS
    """

    def get_user(self):
        if self.user is None:
            self.user = g.user
            if self.user is None:
                raise InvalidUsage("Error authenticating the user")
        return self.user

    def get_user_id(self):
        return self.get_user().id

    def is_admin(self):
        """
        :return: if user is admin
        :rtype: bool
        """
        return self.get_user().is_admin()

    def is_service_user(self):
        """
        :return: if user is service user
        :rtype: bool
        """
        return self.get_user().is_service_user()

    @staticmethod
    def get_data_or_404(func):
        """
        Auth decorator
        :param func:
        :return:
        """

        @wraps(func)
        def decorated_func(*args, **kwargs):
            data = func(*args, **kwargs)
            if data is None:
                raise ObjectDoesNotExist()
            return data

        return decorated_func

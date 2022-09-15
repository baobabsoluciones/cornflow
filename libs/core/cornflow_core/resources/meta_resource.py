"""
This file has all the logic shared for all the resources
"""
# Import from python standard libraries
from functools import wraps
from pytups import SuperDict

# Import from external libraries
from flask_restful import Resource
from flask import g, request
from flask_apispec.views import MethodResource

# Import from internal modules
from cornflow_core.constants import ALL_DEFAULT_ROLES
from cornflow_core.exceptions import InvalidUsage, ObjectDoesNotExist, NoPermission


class BaseMetaResource(Resource, MethodResource):
    """
    The base resource from all methods inherit from.
    """

    DESCRIPTION = ""
    ROLES_WITH_ACCESS = ALL_DEFAULT_ROLES

    def __init__(self):
        super().__init__()
        self.data_model = None
        self.user = None
        self.foreign_data = None
        self.auth_class = None
        self.dependents = None
        self.unique = None
        pass

    """
    METHODS USED FOR THE BASIC CRUD OPERATIONS: GET, POST, PUT, PATCH, DELETE 
    """

    def get_list(self, **kwargs):
        """
        Method to GET all objects

        :param kwargs: the keyword arguments to filter.
        :return: the list of objects
        """
        return self.data_model.get_all_objects(**kwargs)

    def get_detail(self, **kwargs):
        """
        Method to GET one object

        :param kwargs: the keyword arguments to filter
        :return: the specific object
        """
        return self.data_model.get_one_object(**kwargs)

    def post_list(self, data, trace_field="user_id"):
        """
        Method to POST one object

        :param dict data: the data to create a new object
        :param str trace_field: the field that tracks the user that created the object
        :return: the newly created item and a status code of the operation
        """
        data = dict(data)
        data[trace_field] = self.get_user_id()
        item = self.data_model(data)
        if self.foreign_data is not None:
            for fk in self.foreign_data:
                owner = self.foreign_data[fk].query.get(getattr(item, fk))
                if owner is None:
                    raise ObjectDoesNotExist()
                if self.user.id != owner.user_id:
                    raise NoPermission()
        item.save()
        return item, 201

    def post_bulk(self, data, trace_field="user_id"):
        """
        Method to POST a bulk of objects
        :param dict data: a dictionary with key 'data' that holds a list with all the
            objects that are going to be created
        :param str trace_field: the field that tracks the user that created the object
        :return: the newly created items and a status code of the operation
        """
        data = [
            {**el, **{trace_field: self.get_user_id()}} for el in dict(data)["data"]
        ]

        instances = self.data_model.create_bulk(data)
        return instances, 201

    def post_bulk_update(self, data, trace_field="user_id"):
        """"""
        data = [
            {**el, **{trace_field: self.get_user_id()}} for el in dict(data)["data"]
        ]

        instances = []
        for el in data:
            temp_el = dict(SuperDict(el).kfilter(lambda v: v in self.unique))
            temp_instance = self.data_model.query.filter_by(**temp_el).first()
            if temp_instance is not None:
                temp_instance.pre_update(el)
                instances.append(temp_instance)
            else:
                instance = self.data_model(el)
                instances.append(instance)

        self.data_model.create_update_bulk(instances)
        return instances, 201

    def put_detail(self, data, track_user: bool = True, **kwargs):
        """
        Method to PUT one object

        :param dict data: a dict with the data used for updating the object
        :param bool track_user: a control value if the user has to be updated or not
        :param kwargs: the keyword arguments to identify the object
        :return: a message if everything went well and a status code.
        """
        item = self.data_model.get_one_object(**kwargs)
        if item is None:
            raise ObjectDoesNotExist("The data entity does not exist on the database")

        data = dict(data)

        if track_user:
            user_id = kwargs.get("user").get("id") or self.get_user_id()
            data["user_id"] = user_id

        item.update(data)
        return {"message": "Updated correctly"}, 200

    def patch_detail(self, data, track_user: bool = True, **kwargs):
        """
        Method to PATCH one object

        :param dict data: a dict with the data used for updating the object
        :param bool track_user: a control value if the user has to be updated or not
        :param kwargs: the keyword arguments to identify the object
        :return: a message if everything went well and a status code.
        """
        item = self.data_model.get_one_object(**kwargs)

        if item is None:
            raise ObjectDoesNotExist("The data entity does not exist on the database")

        data = dict(data)

        if track_user:
            user_id = kwargs.get("user").get("id") or self.get_user_id()
            data["user_id"] = user_id

        item.patch(data)
        return {"message": "Patched correctly"}, 200

    def delete_detail(self, **kwargs):
        """
        Method to DELETE an object from the database

        :param kwargs: the keyword arguments to identify the object
        :return: a message if everything went well and a status code.
        """
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
        """
        Method not implemented yet
        """
        raise NotImplemented

    def activate_detail(self, **kwargs):
        """
        Method to activate a deactivated object

        :param kwargs: the keyword arguments to identify the object
        :return: the object and a status code.
        """
        item = self.data_model.get_one_object(**kwargs)
        item.activate()
        return item, 200

    """
    AUXILIARY METHODS
    """

    def get_user(self):
        """
        Method to get the user from the request or from the application context

        :return: the user object
        :rtype: :class:`UserBaseModel`
        """
        if self.user is None:
            try:
                self.user = g.user
            except AttributeError:
                self.user = self.auth_class.get_user_from_header(request.headers)
            if self.user is None:
                raise InvalidUsage("Error authenticating the user")
        return self.user

    def get_user_id(self):
        """
        Method to get the user id from the request or from the application context

        :return: the user id
        :rtype: int
        """
        return self.get_user().id

    def is_admin(self):
        """
        Method that returns a boolean value if the user is an admin

        :return: if user is admin
        :rtype: bool
        """
        return self.get_user().is_admin()

    def is_service_user(self):
        """
        Method that returns a boolean value if the user is a service user

        :return: if user is service user
        :rtype: bool
        """
        return self.get_user().is_service_user()

    @staticmethod
    def get_data_or_404(func):
        """
        Decorator to get back a 404 if there is not data
        """

        @wraps(func)
        def decorated_func(*args, **kwargs):
            """
            The function being decorated

            :param args: the arguments of the decorated function
            :param kwargs: the keyword arguments of the decorated function
            :return: the result of the decorated function or it raises an exception of type :class:`ObjectDoesNotExist`
            """
            data = func(*args, **kwargs)
            if data is None:
                raise ObjectDoesNotExist()
            return data

        return decorated_func

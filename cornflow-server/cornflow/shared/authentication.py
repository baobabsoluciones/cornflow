"""

"""

# Global imports
from functools import wraps

from cornflow_core.authentication import BaseAuth
from cornflow_core.exceptions import InvalidData, NoPermission
from cornflow_core.models import ViewBaseModel, PermissionViewRoleBaseModel

# Partial imports
from flask import request, g, current_app

# Internal modules imports
from .const import PERMISSION_METHOD_MAP
from ..models import UserModel, PermissionsDAG


class Auth(BaseAuth):
    def __init__(self, user_model=UserModel):
        super().__init__(user_model)

    def authenticate(self):
        user = self.get_user_from_header(request.headers)
        check = Auth._get_permission_for_request(request, user.id)
        g.user = user
        return True

    @staticmethod
    def dag_permission_required(func):
        """
        DAG permission decorator
        :param func:
        :return:
        """

        @wraps(func)
        def dag_decorator(*args, **kwargs):
            if int(current_app.config["OPEN_DEPLOYMENT"]) == 0:
                user_id = g.user.id
                dag_id = request.json.get("schema", None)
                if dag_id is None:
                    raise InvalidData(
                        error="The request does not specify a schema to use",
                        status_code=400,
                        log_txt=f"Error while user {g.user} tries to access a dag. "
                        f"The schema is not specified in the request.",
                    )
                else:
                    if PermissionsDAG.check_if_has_permissions(user_id, dag_id):
                        # We have permissions
                        return func(*args, **kwargs)
                    else:
                        raise NoPermission(
                            error="You do not have permission to use this DAG",
                            status_code=403,
                            log_txt=f"Error while user {g.user} tries to access dag {dag_id}. "
                            f"The user does not have permission to access the dag.",
                        )
            else:
                return func(*args, **kwargs)

        return dag_decorator

    @staticmethod
    def return_user_from_token(token):
        """
        Function used for internal testing. Given a token gives back the user_id encoded in it.

        :param str token: the given token
        :return: the user id code.
        :rtype: int
        """
        user_id = Auth.decode_token(token)["user_id"]
        return user_id

    """
    START OF INTERNAL PROTECTED METHODS
    """

    @staticmethod
    def _get_permission_for_request(req, user_id):
        method, url = Auth._get_request_info(req)
        current_app.logger.info(f"{getattr(req, 'url_rule').__dict__}")
        user_roles = UserModel.get_one_user(user_id).roles
        if user_roles is None or user_roles == {}:
            raise NoPermission(
                error="You do not have permission to access this endpoint",
                status_code=403,
                log_txt=f"Error while user {user_id} tries to access an endpoint. "
                f"The user does not have any role assigned. ",
            )

        action_id = PERMISSION_METHOD_MAP[method]
        try:
            view_id = ViewBaseModel.query.filter_by(url_rule=url).first().id
        except AttributeError:
            current_app.logger.error(
                "The permission for this endpoint is not in the database."
            )
            raise NoPermission(
                error="You do not have permission to access this endpoint",
                status_code=403,
                log_txt=f"Error while user {user_id} tries to access endpoint. "
                f"The user does not permission to access. ",
            )

        for role in user_roles:
            has_permission = PermissionViewRoleBaseModel.get_permission(
                role_id=role, api_view_id=view_id, action_id=action_id
            )

            if has_permission:
                return True

        raise NoPermission(
            error="You do not have permission to access this endpoint",
            status_code=403,
            log_txt=f"Error while user {user_id} tries to access endpoint {view_id} with action {action_id}. "
            f"The user does not permission to access. ",
        )

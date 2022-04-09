"""

"""
# Global imports
import jwt

# Partial imports
from flask import request, g, current_app
from functools import wraps

# Internal modules imports
from .const import PERMISSION_METHOD_MAP

from cornflow_core.exceptions import InvalidCredentials, InvalidData, NoPermission

from ..models import ApiViewModel, UserModel, PermissionsDAG, PermissionViewRoleModel

from cornflow_core.authentication import BaseAuth


class Auth(BaseAuth):
    def __init__(self, user_model=UserModel):
        super().__init__(user_model)

    def validate_oid_token(self, token, client_id, tenant_id, issuer, provider):
        """
        :param str token:
        :param str client_id:
        :param str tenant_id:
        :param str issuer:
        :param int provider:
        """
        public_key = self._get_public_key(token, tenant_id, provider)
        try:
            decoded = jwt.decode(
                token,
                public_key,
                verify=True,
                algorithms=["RS256"],
                audience=[client_id],
                issuer=issuer,
            )
            return decoded
        except jwt.ExpiredSignatureError:
            raise InvalidCredentials(
                error="The token has expired, please login again", status_code=400
            )
        except jwt.InvalidTokenError:
            raise InvalidCredentials(
                error="Invalid token, please try again with a new token",
                status_code=400,
            )

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
                    )
                else:
                    if PermissionsDAG.check_if_has_permissions(user_id, dag_id):
                        # We have permissions
                        return func(*args, **kwargs)
                    else:
                        raise NoPermission(
                            error="You do not have permission to use this DAG",
                            status_code=403,
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
        user_roles = UserModel.get_one_user(user_id).roles
        if user_roles is None or user_roles == {}:
            raise NoPermission(
                error="You do not have permission to access this endpoint",
                status_code=403,
            )

        action_id = PERMISSION_METHOD_MAP[method]
        view_id = ApiViewModel.query.filter_by(url_rule=url).first().id

        for role in user_roles:
            has_permission = PermissionViewRoleModel.get_permission(
                role_id=role, api_view_id=view_id, action_id=action_id
            )

            if has_permission:
                return True

        raise NoPermission(
            error="You do not have permission to access this endpoint", status_code=403
        )

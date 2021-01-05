from flask import request
from ..models.user import UserModel
from ..schemas.user import UserSchema
from ..shared.authentication import Auth
from ..shared.resource import BaseResource

user_schema = UserSchema()


class UserEndpoint(BaseResource):

    @Auth.auth_required
    def get(self):
        user_id, admin, super_admin = Auth.return_user_info(request)
        if not (admin or super_admin):
            return {}, 400
        users = UserModel.get_all_users()
        ser_users = user_schema.dump(users, many=True)
        return ser_users, 200


class UserDetailsEndpoint(BaseResource):

    @Auth.auth_required
    def get(self, user_id):
        ath_user_id, admin, super_admin = Auth.return_user_info(request)
        if ath_user_id != user_id and not (admin or super_admin):
            return {}, 400
        user = UserModel.get_one_user(user_id)
        ser_users = user_schema.dump(user, many=False)
        return ser_users, 200

import logging as log

from flask import current_app
from sqlalchemy.exc import IntegrityError, DBAPIError

from cornflow_core.authentication import BaseAuth, LDAPBase
from cornflow_core.constants import (
    AUTH_DB,
    AUTH_LDAP,
    AUTH_OID,
    OID_AZURE,
    OID_GOOGLE,
    OID_NONE,
)
from cornflow_core.exceptions import (
    ConfigurationError,
    InvalidCredentials,
    InvalidUsage,
    EndpointNotImplemented,
)
from .meta_resource import BaseMetaResource
from ..shared import database


class LoginBaseEndpoint(BaseMetaResource):
    """
    Base endpoint to perform a login action from a user
    """

    def __init__(self):
        super().__init__()
        self.auth_class = BaseAuth
        self.ldap_class = LDAPBase
        self.user_role_association = None

    def log_in(self, **kwargs):
        auth_type = current_app.config["AUTH_TYPE"]

        if auth_type == AUTH_DB:
            user = self.auth_db_authenticate(**kwargs)
        elif auth_type == AUTH_LDAP:
            user = self.auth_ldap_authenticate(**kwargs)
        elif auth_type == AUTH_OID:
            user = self.auth_oid_authenticate(**kwargs)
        else:
            raise ConfigurationError()

        try:
            token = self.auth_class.generate_token(user.id)
        except Exception as e:
            raise InvalidUsage(f"Error in generating user token: {str(e)}", 400)

        return {"token": token, "id": user.id}, 200

    def auth_db_authenticate(self, username, password):
        user = self.data_model.get_one_object(username=username)

        if not user:
            raise InvalidCredentials()

        if not user.check_hash(password):
            raise InvalidCredentials()

        return user

    def auth_ldap_authenticate(self, username, password):
        ldap_obj = self.ldap_class(current_app.config)
        if not ldap_obj.authenticate(username, password):
            raise InvalidCredentials()
        user = self.data_model.get_one_object(username=username)
        if not user:
            log.info(f"LDAP user {username} does not exist and is created")
            email = ldap_obj.get_user_email(username)
            if not email:
                email = ""
            data = {"username": username, "email": email}
            user = self.data_model(data=data)
            user.dave()

        roles = ldap_obj.get_user_roles(username)

        try:
            self.user_role_association(user.id)
            for role in roles:
                user_role = self.user_role_association(
                    data={"user_id": user.id, "role_id": role}
                )
                user_role.save()

        except IntegrityError as e:
            database.session.rollback()
            log.error(f"Integrity error on user role assignment on log in: {e}")
        except DBAPIError as e:
            database.session.rollback()
            log.error(f"Unknown error on user role assignment on log in: {e}")

        return user

    def auth_oid_authenticate(self, token):
        oid_provider = int(current_app.config["OID_PROVIDER"])

        client_id = current_app.config["OID_CLIENT_ID"]
        tenant_id = current_app.config["OID_TENANT_ID"]
        issuer = current_app.config["OID_ISSUER"]

        if client_id is None or tenant_id is None or issuer is None:
            raise ConfigurationError("The OID provider configuration is not valid")

        if oid_provider == OID_AZURE:
            decoded_token = self.auth_class().validate_oid_token(
                token, client_id, tenant_id, issuer, oid_provider
            )

        elif oid_provider == OID_GOOGLE:
            raise EndpointNotImplemented("The selected OID provider is not implemented")
        elif oid_provider == OID_NONE:
            raise EndpointNotImplemented("The OID provider configuration is not valid")
        else:
            raise EndpointNotImplemented("The OID provider configuration is not valid")

        username = decoded_token["preferred_username"]

        user = self.data_model.get_one_object(username=username)

        if not user:
            log.info(f"OpenID user {username} does not exist and is created")

            data = {"username": username, "email": username}

            user = self.data_model(data=data)
            user.save()

            self.user_role_association(user.id)

            user_role = self.user_role_association(
                {"user_id": user.id, "role_id": int(current_app.config["DEFAULT_ROLE"])}
            )

            user_role.save()

        return user

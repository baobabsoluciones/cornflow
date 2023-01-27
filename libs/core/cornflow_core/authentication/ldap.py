"""
This file implements the class that handles the LDAP connection to authenticate the user on log in.
"""

# Import from libraries
from ldap3 import Server, Connection, ALL

# Import from internal modules
from cornflow_core.constants import ALL_DEFAULT_ROLES, ROLES_MAP
from cornflow_core.exceptions import InvalidCredentials


class LDAPBase:
    """
    Class that handles the LDAP functions to perform, login and queries
    """

    def __init__(self, config):
        self.config = config

    def get_bound_connection(self):
        """
        Method to get the bound connection to ldap

        :return: the connection to ldap
        :rtype: :class:`Connection`
        """

        server = Server(self.config["LDAP_HOST"], get_info=ALL)
        ldap_connection = Connection(
            server,
            self.config["LDAP_BIND_DN"],
            self.config["LDAP_BIND_PASSWORD"],
            auto_bind=True,
        )

        return ldap_connection

    def get_dn_from_user(self, user):
        """
        Method to get the dn string for a given user

        :param str user: the user to get the dn from
        :return: the dn string
        :rtype: string
        """
        if user == self.config["CORNFLOW_SERVICE_USER"]:
            base = self.config["LDAP_SERVICE_BASE"]
        else:
            base = self.config["LDAP_USER_BASE"]
        conn = self.get_bound_connection()
        base_search = base
        search_filter = "(&({}={}))".format(
            self.config['LDAP_USERNAME_ATTRIBUTE'],
            user
        )
        conn.search(base_search, search_filter=search_filter,attributes=['*'])
        try:
            user_dn = conn.response[0]['dn']
        except KeyError:
            raise InvalidCredentials()
        return user_dn
        
    def get_user_attribute(self, user, attribute):
        """
        Method to get one attribute from a user in ldap

        :param str user: the user for the query
        :param str attribute: the attribute for the query
        :return: the value of the attribute or False
        :rtype:
        """
        conn = self.get_bound_connection()
        user_search = self.get_dn_from_user(user)

        user_object = f"(objectclass={self.config['LDAP_USER_OBJECT_CLASS']})"

        conn.search(user_search, user_object, attributes=[attribute])

        if not len(conn.entries):
            return False
        entry = conn.entries[0]
        if attribute not in entry:
            return False
        return entry[attribute][0]

    def get_user_email(self, user):
        """
        Method to get the email of a user from ldap

        :param str user: the user to get the email from
        :return: the email of the user or False
        :rtype:
        """
        email_attribute = self.config.get("LDAP_EMAIL_ATTRIBUTE", False)
        if not email_attribute:
            return False
        return self.get_user_attribute(user, email_attribute)

    def get_user_roles(self, user):
        """
        Method to get the roles assigned to the user in ldap

        :param str user:
        :return: the roles assigned to the user or an empty list
        :rtype: list
        """
        # Reference:
        # https://stackoverflow.com/questions/51341936/how-to-get-groups-of-a-user-in-ldap

        conn = self.get_bound_connection()
        user_search = self.get_dn_from_user(user)
        group_search = self.config["LDAP_GROUP_BASE"]

        search_filter = "(&(objectClass={})(member={}))".format(
            self.config["LDAP_GROUP_OBJECT_CLASS"], user_search
        )
        conn.search(group_search, search_filter=search_filter, attributes=["cn"])
        if not len(conn.entries):
            return []

        # first element is the cn string, the second is the USER_BASE
        # we only want the cn string
        roles = [el.cn[0] for el in conn.entries]
        env_to_role = {
            "LDAP_GROUP_TO_ROLE_" + str.upper(ROLES_MAP[k]): k
            for k in ALL_DEFAULT_ROLES
        }
        group_to_role = {self.config.get(k, ""): v for k, v in env_to_role.items()}
        relevant_groups = group_to_role.keys() & set(roles)
        return [group_to_role[k] for k in relevant_groups]

    def authenticate(self, user, password):
        """
        Method to authenticate a user against a ldap server

        :param str user: the user to authenticate
        :param str password: the password to authenticate the user
        :return: if the user is authenticated
        :rtype:
        """
        self.get_bound_connection()
        user_dn = self.get_dn_from_user(user)
        c = Connection(self.config["LDAP_HOST"], user=user_dn, password=password)
        response = c.bind()
        c.unbind()
        return response

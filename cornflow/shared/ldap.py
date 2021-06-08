"""

"""
from ldap3 import Server, Connection, ALL
from cornflow.shared.const import ALL_DEFAULT_ROLES, ROLES_MAP


class LDAP:
    """
    Class that handles the LDAP functions to perform, login and queries
    """

    def __init__(self, config, g):
        self.config = config
        self.g = g

    def get_bound_connection(self):
        """

        :return:
        :rtype:
        """
        try:
            return self.g.ldap_connection
        except:
            pass
        server = Server(self.config["LDAP_HOST"], get_info=ALL)
        ldap_connection = Connection(
            server,
            self.config["LDAP_BIND_DN"],
            self.config["LDAP_BIND_PASSWORD"],
            auto_bind=True,
        )
        try:
            self.g.ldap_connection = ldap_connection
        except:
            pass
        return ldap_connection

    def get_dn_from_user(self, user):
        """

        :param str user:
        :return:
        :rtype:
        """
        return "%s=%s,%s" % (
            self.config["LDAP_USERNAME_ATTRIBUTE"],
            user,
            self.config["LDAP_USER_BASE"],
        )

    def get_user_attribute(self, user, attribute):
        conn = self.get_bound_connection()
        user_search = self.get_dn_from_user(user)

        user_object = "(objectclass={})".format(self.config["LDAP_USER_OBJECT_CLASS"])

        conn.search(user_search, user_object, attributes=[attribute])

        if not len(conn.entries):
            return False
        entry = conn.entries[0]
        if attribute not in entry:
            return False
        return entry[attribute][0]

    def get_user_email(self, user):
        """

        :param str user:
        :return:
        :rtype:
        """
        email_attribute = self.config.get("LDAP_EMAIL_ATTRIBUTE", False)
        if not email_attribute:
            return False
        return self.get_user_attribute(user, email_attribute)

    def get_user_roles(self, user):
        # Reference:
        # https://stackoverflow.com/questions/51341936/how-to-get-groups-of-a-user-in-ldap
        conn = self.get_bound_connection()
        user_search = self.get_dn_from_user(user)
        group_search = self.config["LDAP_GROUP_BASE"]
        # TODO: memberUid is not universal. For some objectClass it's "member"
        search_filter = "(&(objectClass={})(memberUid={}))".format(
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

        :param str user:
        :param str password:
        :return:
        :rtype:
        """
        self.get_bound_connection()
        user_dn = self.get_dn_from_user(user)
        c = Connection(self.config["LDAP_HOST"], user=user_dn, password=password)
        response = c.bind()
        c.unbind()
        return response

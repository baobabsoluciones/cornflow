"""

"""
from flask import g, current_app
from ldap3 import Server, Connection, ALL


class LDAP:
    """
    Class that handles the LDAP functions to perform, login and queries
    """

    @staticmethod
    def get_bound_connection():
        """

        :return:
        :rtype:
        """
        if "ldpa_connection" in g:
            return g.ldap_connection
        server = Server(current_app.config["LDAP_HOST"], get_info=ALL)
        g.ldap_connection = Connection(
            server,
            current_app.config["LDAP_BIND_DN"],
            current_app.config["LDAP_BIND_PASSWORD"],
            auto_bind=True,
        )
        return g.ldap_connection

    @staticmethod
    def get_dn_from_user(user):
        """

        :param str user:
        :return:
        :rtype:
        """
        return "%s=%s,%s" % (
            current_app.config["LDAP_USERNAME_ATTRIBUTE"],
            user,
            current_app.config["LDAP_USER_BASE"],
        )

    @staticmethod
    def get_user_email(user):
        """

        :param str user:
        :return:
        :rtype:
        """
        email_attribute = current_app.config.get("LDAP_EMAIL_ATTRIBUTE", False)
        if not email_attribute:
            return False
        conn = LDAP.get_bound_connection()
        user_search = LDAP.get_dn_from_user(user)

        user_object = "(objectclass=%s)" % (
            current_app.config["LDAP_USER_OBJECT_CLASS"],
        )

        conn.search(user_search, user_object, attributes=[email_attribute])

        if len(conn.entries) < 1:
            return False

        return getattr(conn.entries[0], email_attribute, False)[0]

    @staticmethod
    def authenticate(user, password):
        """

        :param str user:
        :param str password:
        :return:
        :rtype:
        """
        s = Server(current_app.config["LDAP_HOST"], get_info=ALL)
        user_dn = LDAP.get_dn_from_user(user)

        c = Connection(current_app.config["LDAP_HOST"], user=user_dn, password=password)

        if not c.bind():
            c.unbind()
            return False

        c.unbind()
        return True

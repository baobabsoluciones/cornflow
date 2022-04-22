"""
THIS FILE CONTAINS THE CONSTANTS RELATED WITH THE AUTH PROCESS
"""

# These codes and names are inherited from flask app-builder in order to have the same names and values
# as this library that is the base of airflow
AUTH_DB = 1
AUTH_LDAP = 2
AUTH_OAUTH = 4
AUTH_OID = 0

# Providers of open ID:
OID_NONE = 0
OID_AZURE = 1
OID_GOOGLE = 2

# AZURE OPEN ID URLS
OID_AZURE_DISCOVERY_COMMON_URL = (
    "https://login.microsoftonline.com/common/.well-known/openid-configuration"
)
OID_AZURE_DISCOVERY_TENANT_URL = (
    "https://login.microsoftonline.com/{tenant_id}/.well-known/openid-configuration"
)

#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Modified configuration for the Airflow webserver using LDAP"""
import os

from airflow import configuration as conf

from flask_appbuilder.security.manager import AUTH_LDAP

basedir = os.path.abspath(os.path.dirname(__file__))

# ----------------------------------------------------
# AUTHENTICATION CONFIG
# ----------------------------------------------------
# For details on how to set up each of the following authentication, see
# http://flask-appbuilder.readthedocs.io/en/latest/security.html# authentication-methods
# for details.

# The authentication type
# AUTH_LDAP : Is for LDAP
AUTH_TYPE = AUTH_LDAP

# Will allow user self registration
AUTH_USER_REGISTRATION = True
# The default user self registration role
AUTH_USER_REGISTRATION_ROLE = "Op"

# When using LDAP Auth, setup the ldap server
AUTH_LDAP_SERVER = os.environ.get("AIRFLOW_LDAP_URI")
AUTH_LDAP_USE_TLS = os.environ.get("AIRFLOW_LDAP_USE_TLS")
AUTH_LDAP_SEARCH = os.environ.get("AIRFLOW_LDAP_SEARCH")
AUTH_LDAP_UID_FIELD = os.environ.get("AIRFLOW_LDAP_UID_FIELD")

# For a typical OpenLDAP setup (where LDAP searches require a special account):
# The user must be the LDAP USER as defined in LDAP_ADMIN_USERNAME
AUTH_LDAP_BIND_USER = os.environ.get("AIRFLOW_LDAP_BIND_USER")
AUTH_LDAP_BIND_PASSWORD = os.environ.get("AIRFLOW_LDAP_BIND_PASSWORD")

# a mapping from LDAP DN to a list of FAB roles
AUTH_ROLES_MAPPING = {
    os.environ.get("AIRFLOW_LDAP_ROLE_MAPPING_ADMIN"): ["Admin"],
    os.environ.get("AIRFLOW_LDAP_ROLE_MAPPING_OP"): ["Op"],
    os.environ.get("AIRFLOW_LDAP_ROLE_MAPPING_PUBLIC"): ["Public"],
    os.environ.get("AIRFLOW_LDAP_ROLE_MAPPING_VIEWER"): ["User"],
}
AUTH_ROLES_SYNC_AT_LOGIN = True

# the LDAP user attribute which has their role DNs
AUTH_LDAP_GROUP_FIELD = os.environ.get("AIRFLOW_LDAP_GROUP_FIELD")

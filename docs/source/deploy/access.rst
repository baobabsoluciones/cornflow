Access control
-----------------------

Cornflow supports multi-user access using password encryption authentication. The user needs to authenticate at least once with the cornflow server to obtain a token that allows him to continue operating.
In this section we will explain the workflow and data process when create users, delete them or change the user´s access password.

User access data
*********************

Right now cornflow has two valid user authentication methods. The first is AUTH_DB, which in addition to being the one that is activated by default, is the easiest to configure since the authentication is carried out against the application itself that stores the credentials in encrypted form.
The second method is AUTH_LDAP. This method allows you to link cornflow with your own security directory and thus the application will delegate the authentication of the users.

With Auth-DB (default)
^^^^^^^^^^^^^^^^^^^^^^^^^

Cornflow has an environment variable to control the type of authentication we want to activate::

    AUTH_TYPE = 1 (Auth-DB default method)

User datatable default content::

    user name
    password
    first name
    last name
    email
    admin-super admin (deprecated)
    auditory fields (cornflow saves information such us the date of creation or modification of the user)

The password is stored encrypted in the database. If a user does not have a password an email will be sent with the temporary access password.

With Auth-LDAP
^^^^^^^^^^^^^^^^^

As we saw previously cornflow has an environment variable to control the type of authentication we want to activate::

    AUTH_TYPE = 2 (Auth-LDAP authentication)

This authentication will be through a unique user code "common name" (user name) and password. The password will never be stored on the cornflow server but other data will be stored that will allow users to migrate or import to change the type of authentication. This operation cannot be performed with the server running.
In the event that you consult the connection through LDAP, the following information will be requested from the server.,

User datatable default content::

    user name
    email
    auditory fields - (cornflow saves information such us the date of creation or modification of the user)

User data objects request from LDAP server::

    password validation (only for compare)
    email
    role

No password is stored in the database. No confirmation email is sent with a temporary access password.

**LDAP authentication library**

In cornflow we have used `this library <https://github.com/tedivm/tedivms-flask>`_ to develop authentication methods. With this configuration the cornflow backend will be connected to external LDAP server:

Any installation can run with Auth-LDAP as its backend with these settings::

    LDAP_HOST - ldap server address 
    LDAP_BIND_DN - ldap admin search for domain
    LDAP_BIND_PASSWORD - ldap admin search password
    LDAP_USERNAME_ATTRIBUTE - The name of the attribute that represents the unique ID of the user
    LDAP_USER_BASE - The base DN subtree that is used when searching for user entries on the LDAP server
    LDAP_USER_OBJECT_CLASS - The object classes are defined in the LDAP directory schema (they constitute a class hierarchy there)
    LDAP_GROUP_OBJECT_CLASS - Filter used for returning a list of group member entries that are in the LDAP base DN (groups) subtree
    LDAP_GROUP_ATTRIBUTE - The name of the attribute in the group search filter that represents the group name
    LDAP_GROUP_BASE - The base DN subtree that is used when searching for group entries on the LDAP server
    LDAP_USE_TLS - TLS communication protocol (Transport Layer Security) over 636 port
    LDAP_EMAIL_ATTRIBUTE - ldap email user object

Roles definition
*********************

In cornflow there is a differentiation between three user roles with different characteristics::

    Admin - admin user can manage the rest of cornflow users and also has access to make changes to the airflow platform
    Service - service user role for cornflow and airflow communication
    Viewer - read only user
    Planner - the general user of cornflow can create jobs and send models to solve

Each role is stored in a table linking the role code with the permissions on the application.
In addition, there is a temporary link between the user and his role that will not be updated until the login operation is performed again.

**User role assignation (in all authentication types)**

In this table we have the role assignment for each user. May be more than one role assigned to the user.

Data storage::

    User ID - internal cornflow user identification 
    Role ID assigned - role identification assigned to the user

**Role data storage (in all authentication types)**

Master data of roles in application::

    Role ID - internal cornflow role identification
    Role name - role name

Roles with Auth-LDAP
^^^^^^^^^^^^^^^^^^^^^^^^

In the cornflow server deployment, the LDAP server roles will be configured through environment variables. Cornflow roles to bind to ldap server::

    LDAP_GROUP_TO_ROLE_SERVICE
    LDAP_GROUP_TO_ROLE_ADMIN 
    LDAP_GROUP_TO_ROLE_VIEWER
    LDAP_GROUP_TO_ROLE_PLANNER

In this way, the user permissions and their defined roles are always done within the cornflow application and allow the authentication configuration to be changed in the future.

Cornflow interactions with airflow (service user)
*****************************************************

Cornflow ⇒ Airflow
^^^^^^^^^^^^^^^^^^^^^^

Not all cornflow users can access airflow. A role defined in the application will give access to perform actions that involve communication with airflow through the user defined in the previous point.
If the user has access to airflow, in each communication, the username and password that provides access to the platform will be provided by this environment variables::

    AIRFLOW_USER - airflow user name for login in airflow and manage dags
    AIRFLOW_PWD - airflow user password

Airflow does not have to be connected via LDAP. Linking them does not affect how cornflow works. Airflow receives a username and password that has privileges to perform actions defined in the system by cornflow.
The cornflow user profile in airflow must have the following permissions::

    administrate connections
    administrate DAG
    administrative Tasks
    administrate DAG Runs
    administrator Jobs

If airflow also connects through LDAP to the same active directory, it will be necessary in the deployment configuration to bind the user that communicates cornflow with the role that gives the previously defined permissions.
The user who operates airflow through cornflow may not be the same user who has the role of system administrator of the platform.

**User access to dags**

The user access to each dag in airflow can be controlled in cornflow. Cornflow store a table with dags and have roles that give access to each dag individually.

Airflow ⇒ Cornflow
^^^^^^^^^^^^^^^^^^^^^^^

Airflow use a cornflow service rights that allow it to do some operations. It´s used to get and post to any user’s instances and executions. In this way this role restrict for doing admin stuff (e.g., manage users or delete them)
Service user is a good solution for doing all the data interaction between applications. You have only to pay attention to one account for set permissions and key values on deployment::

    CORNFLOW_SERVICE_USER - service user account name for communications between cornflow and airflow (default value `service_user`)
    CORNFLOW_SERVICE_MAIL - service user account email (default value `service_user@cornflow.com`)
    CORNFLOW_SERVICE_PWD - service user account password (default value `Service_user1234`)

This connection is provided by::

    AIRFLOW_CONN_CF_URI="cornflow://CORNFLOW_SERVICE_USER:CORNFLOW_SERVICE_PWD@cornflowserveraddress:cornflowserverport"

Keep in mind to change default credentials when going to production.

Manage cornflow users
***********************

In the cornflow image, if no environment variables are set, an admin user is created with these credentials::

    CORNFLOW_ADMIN_USER - cornflow_admin
    CORNFLOW_ADMIN_EMAIL - cornflow_admin@cornflow.com
    CORNFLOW_ADMIN_PWD - Cornflow_admin1234

It is advisable to change the default admin user and keep the password in a safe place.

To create a user, you must interact with the cornflow application through an `endpoint of its API <https://baobabsoluciones.github.io/cornflow/dev/endpoints.html#module-cornflow.endpoints.user>`_. Check the API docs for the users `here <https://baobabsoluciones.github.io/corn/stable-rest-api-ref.html#tag/Users>`_. It is only possible to create new cornflow admin user using another one with those privileges.

Manage airflow users
***********************

The default administrator user for airflow and flower will be::

    AIRFLOW_USER - admin
    AIRFLOW_PWD - admin

It is advisable to change the default admin user and keep the password in a safe place.
`Access Control of Airflow Webserver UI <https://airflow.apache.org/docs/apache-airflow/stable/security/access-control.html>`_ is handled by Flask AppBuilder (FAB). Please read its related security document regarding its `security model <http://flask-appbuilder.readthedocs.io/en/latest/security.html>`_.

Remember to configure all authentication, users and access before passing to production. Check the previous section for more information: :ref:`Production deployment and security`.

External LDAP authentication server requirements
****************************************************

The requirements to communicate cornflow with an LDAP server are the following::

    An authentication server with support for the LDAPv3 protocol.
    The LDAP server must be visible at all times on the network by the cornflow server.
    The users created in the LDAP server must have unique identifiers and roles defined to relate them to the existing ones in cornflow.
    All users must have a unique user identifier and the password protocol will be the one provided by the LDAP authentication system.
    Users must have a field to store the email.
    The type of LDAP object used to search for users (objectClass)

For example, here are some example values for each of the ldap_user_type object::

        (objectClass=posixAccount) for RFC-2037 and RFC-2037bis
        (objectClass=sambaSamAccount) for SAMBA 3.0.x LDAP extension
        (objectClass=user) for MS-AD
        (objectClass=*) for Default

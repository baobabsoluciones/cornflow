Access control
-----------------------

Cornflow supports multi-user access using password encryption authentication. In this section we will see how to create users, delete them or change the user´s access password.

Manage cornflow users
***********************

In the cornflow image, if no environment variables are set, a super-admin user is created with these credentials::

    name - user@cornflow.com
    password - cornflow1234

It is advisable to change the default super-admin user and keep the password in a safe place.

To create a user, you must interact with the cornflow application through an `endpoint of its API <https://baobabsoluciones.github.io/corn/dev/endpoints.html#module-cornflow.endpoints.user>`_. Check the API docs for the users `here <https://baobabsoluciones.github.io/corn/stable-rest-api-ref.html#tag/Users>`_. It is only possible to create new cornflow admin user using another one with those privileges.

In cornflow there is a differentiation between three user roles with different characteristics::

    super-admin - This user can manage the rest of cornflow users and also has access to make changes to the airflow platform
    admin - This user can manage the rest of the cornflow users but does not have privileged access to the airflow service
    user - The general user of cornflow can create jobs and send models to solve

Manage airflow users
***********************

The default administrator user for airflow and flower will be::

    name - admin
    password - admin

It is advisable to change the default admin user and keep the password in a safe place.
`Access Control of Airflow Webserver UI <https://airflow.apache.org/docs/apache-airflow/stable/security/access-control.html>`_ is handled by Flask AppBuilder (FAB). Please read its related security document regarding its `security model <http://flask-appbuilder.readthedocs.io/en/latest/security.html>`_.

Remember to configure all authentication, users and access before passing to production. Check the previous section for more information: :ref:`Production deployment and security`.
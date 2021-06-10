Production deployment and security
---------------------------------------

It is time to deploy Cornflow in production. To do this, first, you need to make sure that the airflow is itself `production-ready <https://airflow.apache.org/docs/apache-airflow/stable/production-deployment.html>`_.

Database backend
*****************

Running the default docker-compose setup in production can lead to data loss in multiple scenarios. If you want to run production-grade Cornflow, make sure you configure the backend to be an external PostgreSQL.
You can change the backend using the following config::

    DATABASE_URL=postgres://myuser:myuserpwd@myserverip:5432/cornflow

SSL
******

At the moment cornflow does not have built-in `SSL <https://en.wikipedia.org/wiki/Transport_Layer_Security>`_ support. You can use a reverse proxy service such as `Nginx <http://nginx.org/>`_ to give adequate security to the connection with your server.
Please go to the `Nginx documentation page <http://nginx.org/en/docs/http/configuring_https_servers.html>`_ to correctly configure your server's certificates. 

This is a Nginx configuration template (``/etc/nginx/conf.d/mysite.conf``) that we can use to configure the ssl encryption with the cornflow service::

    server {
       listen 443 ssl;
       server_name mycornflowsite.com;
       location / {
       rewrite ^/v1/(.*)$ /$1 break;
         proxy_pass http://localhost:5000;
         proxy_set_header Host $host;
         proxy_redirect off;
         proxy_http_version 1.1;
         proxy_set_header Upgrade $http_upgrade;
         proxy_set_header Connection "upgrade";
       }
       ssl_certificate /pathtocertificate/mysite.crt;
       ssl_certificate_key /pathtocertificatekey/mysite.key;
       error_page 400 /400.json;
       location /400.json {
           return 400 '{"error":{"code":400,"message":"Bad Request"}}';
       }
       error_page 403 /403.json;
       location /403.json {
           return 403 '{"error":{"code":403,"message": "Forbidden"}}';
       }
       error_page 500 /500.json;
       location /500.json {
           return 500 '{"error":{"code":500,"message":"Internal Server Error"}}';
       }
    }

Enforce security
********************

When using cornflow in a production environment, the usernames and passwords should be stored in a safe place. In the deployment through docker-compose you can connect the environment variables with your KMS system.
If you are running docker services in production, it is also convenient to use the `docker secret manager <https://docs.docker.com/engine/swarm/secrets/#use-secrets-in-compose>`_.

It is also recommended to put a password in the celery broker for the production environment. In all airflow services, the redis environment variable should be secured with a key::

    REDIS_PASSWORD="myredispassword"

Flower has by default a `basic authentication <https://flower.readthedocs.io/en/latest/auth.html>`_ shared with the airflow server in the deployment.

LDAP Authentication
**********************

Cornflow supports user authentication through LDAP protocol. This means that you can configure the application to point to your security application server and cornflow reads the user management of your organization.
To activate the functionality that supports this type of access, it is necessary set the value of the ldap environment variables before starting the cornflow service.

In the `repository <https://raw.githubusercontent.com/baobabsoluciones/corn/master/docker-compose-cornflow-ldap.yml>`_ we have an example of deployment with docker to configure access with LDAP protocol::

    docker-compose -f docker-compose-cornflow-ldap.yml up -d

With this docker template following users will be create in openldap server::

    User ``administrator`` with password ``adminnistrator1234``
    Service user ``cornflow`` with password ``cornflow1234``
    Viewer user ``viewer`` with password ``viewer1234``
    General user ``planner`` with password ``planner1234``

Airflow does support this functionality and therefore it should be activated in the production deployment. To learn more about how to enable LDAP in airflow, see this `page <https://airflow.apache.org/docs/apache-airflow/1.10.1/security.html#ldap>`_.

Airflow user
****************

It is not necessary to use the admin user to communicate cornflow with airflow. We recommend giving cornflow a user who has restricted permissions on airflow. 
A good start is to create a role for the cornflow application (cornflowrole) with permissions to manage DAGs, tasks, and jobs. Something that is not necessary is to give permissions to manage other users or configurations of the platform.
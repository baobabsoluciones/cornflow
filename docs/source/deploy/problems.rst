Known problems
------------------

When deploying cornflow through docker, you may run into one of the following problems. It is difficult to cover all the possibilities but we will try to update the documentation to include at least those that happen to us.

Situations
*************

Development
^^^^^^^^^^^^^^^

Problem: Possible error with psycopg2

    Error: Error pg_config executable not found.  
    
    Possible solution: The installation of the psycopg2 may generate an error because it does not find the pg_config file. One way to solve this problem is to previously install libpq-dev which installs pg_config ("sudo apt install libpq-dev")

Docker build
^^^^^^^^^^^^^^^

Problem: The volume airflow_config can´t be mounted.

    Error: Unable to prepare context: path "local_path_to_docker-compose.yml/airflow_config"  
    
    Possible solution: Start docker-compose.yml from root path of cloned corn repository.

Problem: The Dockerfile is not found by docker-compose. 
    
    Error: Not found or failed to solve with frontend dockerfile.v0: failed to read dockerfile 
    
    Possible solution: Start from the same path of Dockerfile or modify the location of it into the build section of docker-compose file.

Problem: The image is not installing any linux pkg.
    
    Error: gcc exited code error 1 
    
    Possible solution: Try to use docker platform argument "—platform linux/amd64" for build image with extended compatibility.

Cornflow database
^^^^^^^^^^^^^^^^^^^^^^

Problem: Cornflow can´t reach postgres internal database

    Error: sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not translate host name "host_database" to address: Name or service not known 
    
    Possible solution: See again the name given to CORNFLOW_DB_HOST environment variable in docker-compose file.

Running cornflow-server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Problem: Users were not created when cornflow started

    Error: usage: manage.py [-?] {db,create_admin_user,create_service_user,access_init,register_base_assignations,register_actions,register_views,register_roles,update_views,clean_historic_data,shell,runserver} ...

    Possible solution: If you have modified the entrypoint script, checks that the conditions are met in the execution of python mange.py create_admin_user/create_service_user.

Flower 
^^^^^^^^^^

Problem: Can´t login to flower GUI

    Error: Access denied
    
    Possible solution: The admin user and password is the same than airflow.

Airflow
^^^^^^^^^^^

Problem: Can´t login to airflow GUI

    Error: Bad Request The CSRF session token is missing

    Possible solution: Delete cookies from web browser.

Ldap docker
^^^^^^^^^^^^^^^^

Problem: Can´t login to flower GUI

    Error: Access denied
    
    Possible solution: If airflow goes to ldap config, and you don´t give any values to AIRFLOW_USER and AIRFLOW_PWD, the default values are "admin/admin"

Problem: Can´t login to airflow GUI

    Error: Access denied

    Possible solution: User is not same as normal deployment

Problem: Openldap docker container don´t start

    Error: Can't parse ldif entry on line 1

    Possible solution: Some entry on ``*.ldif`` file has not properly defined and slapd can't start and populate the ldap server

Problem: Openldap does not show entries from ldif file 

    Error: failed: bash ls -l not ldif on path

    Possible solution: Try to mount openldap volume with full local path of ldif folder in your machine
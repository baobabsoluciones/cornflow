Known issues
------------------

When deploying cornflow through docker, you may run into one of the following problems. It is difficult to cover all the possibilities but we will try to update the documentation to include at least those that happen to us.

Situations
*************

Development
^^^^^^^^^^^^^^^

Issue: Possible error with psycopg2

    Error: Error pg_config executable not found.  
    
    Possible solution: The installation of the psycopg2 may generate an error because it does not find the pg_config file. One way to solve this problem is to previously install libpq-dev which installs pg_config ("sudo apt install libpq-dev")

Docker build
^^^^^^^^^^^^^^^

Issue: The volume airflow_config can´t be mounted.

    Error: Unable to prepare context: path "local_path_to_docker-compose.yml/airflow_config"  
    
    Possible solution: Start docker-compose.yml from root path of cloned corn repository.

Issue: The Dockerfile is not found by docker-compose. 
    
    Error: Not found or failed to solve with frontend dockerfile.v0: failed to read dockerfile 
    
    Possible solution: Start from the same path of Dockerfile or modify the location of it into the build section of docker-compose file.

Issue: The image is not installing any linux pkg.
    
    Error: gcc exited code error 1 
    
    Possible solution: Try to use docker platform argument "—platform linux/amd64" for build image with extended compatibility.

Cornflow database
^^^^^^^^^^^^^^^^^^^^^^

Issue: Cornflow can´t reach postgres internal database

    Error: sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not translate host name "host_database" to address: Name or service not known 
    
    Possible solution: See again the name given to CORNFLOW_DB_HOST environment variable in docker-compose file.

Running cornflow-server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Issue: Users were not created when cornflow started

    Error: usage: flask [-?] {db,create_admin_user,create_service_user,access_init,register_base_assignations,register_actions,register_views,register_roles,update_views,clean_historic_data,shell,runserver} ...

    Possible solution: If you have modified the entrypoint script, checks that the conditions are met in the execution of flask create_admin_user/create_service_user.

Flower 
^^^^^^^^^^

Issue: Can't login to flower GUI

    Error: Access denied
    
    Possible solution: The admin user and password is the same than airflow.

Scheduler
^^^^^^^^^^^
Issue: Can't find Scheduler logs. 
    
    Error: 
    
    .. code-block:: bash

        FileNotFoundError: [Errno 2] No such file or directory: '/usr/local/airflow/logs/scheduler/2024-07-01'
        PermissionError: [Errno 13] Permission denied: '/usr/local/airflow/logs/scheduler'
    
    Possible solution: Both errors usually occur when using the root user and root group as the owner of the directory. One possible solution is:

    .. code-block:: bash

        sudo chown -R 1000:1000 cornflow/cornflow-server/airflow_config/logs
      
    You should use 1000 because it is the UID and GID of the first user and group different from root.

Airflow
^^^^^^^^^^^

Issue: Can't login to airflow GUI

    Error: Bad Request The CSRF session token is missing

    Possible solution: Delete cookies from web browser.

Ldap docker
^^^^^^^^^^^^^^^^

Issue: Can't login to flower GUI

    Error: Access denied
    
    Possible solution: If airflow goes to ldap config, and you don´t give any values to AIRFLOW_USER and AIRFLOW_PWD, the default values are "admin/admin"

Issue: Can't login to airflow GUI

    Error: Access denied

    Possible solution: User is not same as normal deployment

Issue: Openldap docker container don´t start

    Error: Can't parse ldif entry on line 1

    Possible solution: Some entry on ``*.ldif`` file has not properly defined and slapd can't start and populate the ldap server

Issue: Openldap does not show entries from ldif file 

    Error: failed: bash ls -l not ldif on path

    Possible solution: Try to mount openldap volume with full local path of ldif folder in your machine

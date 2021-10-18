# Cornflow init script for Dockerfile ENTRYPOINT
from logging import error
import subprocess
import os
from cryptography.fernet import Fernet

os.chdir("/usr/src/app")

###################################
# Global defaults and back-compat #
###################################
# Airflow global default conn 
os.environ.setdefault("AIRFLOW_USER","admin")
os.environ.setdefault("AIRFLOW_PWD","admin")
os.environ.setdefault("AIRFLOW_URL","http://webserver:8080")
os.environ.setdefault("CORNFLOW_URL","http://cornflow:5000")
os.environ.setdefault("AUTH_TYPE","1")
os.environ.setdefault("FLASK_APP","cornflow.app")
os.environ.setdefault("FLASK_ENV","development")
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())

# Cornflow db defaults
os.environ.setdefault("CORNFLOW_DB_HOST","cornflow_db")
os.environ.setdefault("CORNFLOW_DB_PORT","5432")
os.environ.setdefault("CORNFLOW_DB_USER","cornflow")
os.environ.setdefault("CORNFLOW_DB_PASSWORD","cornflow")
os.environ.setdefault("CORNFLOW_DB","cornflow")
os.environ.setdefault("CORNFLOW_DB_CONN","postgres://"+os.getenv("CORNFLOW_DB_USER")+":"+os.getenv("CORNFLOW_DB_PASSWORD")+"@"+os.getenv("CORNFLOW_DB_HOST")+":"+os.getenv("CORNFLOW_DB_PORT")+"/"+os.getenv("CORNFLOW_DB"))
os.environ.setdefault("DATABASE_URL",os.getenv("CORNFLOW_DB_CONN"))

# Platform service users
os.environ.setdefault("CORNFLOW_ADMIN_USER","cornflow_admin")
os.environ.setdefault("CORNFLOW_ADMIN_EMAIL","cornflow_admin@cornflow.com")
os.environ.setdefault("CORNFLOW_ADMIN_PWD","cornflowadmin1234")
os.environ.setdefault("CORNFLOW_SERVICE_USER","service_user")
os.environ.setdefault("CORNFLOW_SERVICE_EMAIL","service_user@cornflow.com")
os.environ.setdefault("CORNFLOW_SERVICE_PWD","serviceuser1234")

# LDAP parameters for active directory
os.environ.setdefault("LDAP_PROTOCOL_VERSION","3")
os.environ.setdefault("LDAP_BIND_PASSWORD","admin")
os.environ.setdefault("LDAP_BIND_DN","cn=admin,dc=example,dc=org")
os.environ.setdefault("LDAP_USE_TLS","False")
os.environ.setdefault("LDAP_HOST","ldap://openldap:389")
os.environ.setdefault("LDAP_USERNAME_ATTRIBUTE","cn")
os.environ.setdefault("LDAP_USER_BASE","ou=users,dc=example,dc=org")
os.environ.setdefault("LDAP_EMAIL_ATTRIBUTE","mail")
os.environ.setdefault("LDAP_USER_OBJECT_CLASS","inetOrgPerson")
os.environ.setdefault("LDAP_GROUP_OBJECT_CLASS","posixGroup")
os.environ.setdefault("LDAP_GROUP_ATTRIBUTE","cn")
os.environ.setdefault("LDAP_GROUP_BASE","ou=groups,dc=example,dc=org")
os.environ.setdefault("LDAP_GROUP_TO_ROLE_SERVICE","service")
os.environ.setdefault("LDAP_GROUP_TO_ROLE_ADMIN","administrators")
os.environ.setdefault("LDAP_GROUP_TO_ROLE_VIEWER","viewers")
os.environ.setdefault("LDAP_GROUP_TO_ROLE_PLANNER","planners")

# Cornflow logging and storage config
os.environ.setdefault("CORNFLOW_LOGGING","")
  
# Check LDAP parameters for active directory and show message
if os.getenv("AUTH_TYPE") == 2:
    print("WARNING: Cornflow will be deployed with LDAP Authorization. Please review your ldap auth configuration.")

# check database param from docker env
if os.getenv("DATABASE_URL") is None :
	print("FATAL: you need to provide a postgres database for Cornflow")

# set logrotate config file
if os.getenv("CORNFLOW_LOGGING") == "file" : 
    try:
      conf = "/usr/src/app/log/*.log {\n\
        rotate 30\n \
        daily\n\
        compress\n\
        size 20M\n\
        postrotate\n\
         kill -HUP \$(cat /usr/src/app/gunicorn.pid)\n \
        endscript}"
      logrotate = subprocess.run("cat > /etc/logrotate.d/cornflow <<EOF\n" + conf + "\nEOF", shell=True)
      out_logrotate = logrotate.stdout
      print(out_logrotate)

    except (error):
        print(error)

# make initdb and/or migrations
dbup = subprocess.run(["python","manage.py","db","upgrade"],stdout=subprocess.PIPE,universal_newlines=True)
out_dbup = dbup.stdout
print(out_dbup)

# make initdb access control
access_init = subprocess.run(["python","manage.py","access_init"],stdout=subprocess.PIPE,universal_newlines=True)
out_accinit= access_init.stdout
print(out_accinit)

# create user if auth type is db
if os.getenv("AUTH_TYPE") == 1 :
  # create cornflow admin user
  admincmd = "python manage.py create_admin_user --username="+os.getenv("CORNFLOW_ADMIN_USER")+" --email="+os.getenv("CORNFLOW_ADMIN_EMAIL")+" --password="+os.getenv("CORNFLOW_ADMIN_PWD")
  createadmin = subprocess.run([admincmd],stdout=subprocess.PIPE,universal_newlines=True)
  out_createadmin = createadmin.stdout
  print(out_createadmin)
  # create cornflow service user
  svccmd = "python manage.py create_service_user --username="+os.getenv("CORNFLOW_SERVICE_USER")+" --email="+os.getenv("CORNFLOW_SERVICE_EMAIL")+" --password="+os.getenv("CORNFLOW_SERVICE_PWD")
  createsvc = subprocess.run([svccmd],stdout=subprocess.PIPE,universal_newlines=True)
  out_createsvc = createsvc.stdout
  print(out_createsvc) 
# execute gunicorn application
subprocess.run(["/usr/local/bin/gunicorn","-c","cornflow/gunicorn.py","cornflow:create_app('"+os.getenv("FLASK_ENV")+"')"])
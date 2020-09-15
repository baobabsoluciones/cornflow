#!/bin/bash
python manage.py db init
python manage.py db migrate
python manage.py db upgrade
python manage.py create_super_user
flask run -h 0.0.0.0

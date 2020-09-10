#!/bin/bash
python manage.py db init
python manage.py db migrate
python manage.py db upgrade
flask run -h 0.0.0.0

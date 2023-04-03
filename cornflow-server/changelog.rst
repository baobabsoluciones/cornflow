version 1.0.2
---------------

- released: 2023-03-17
- description: fixes error on startup on google cloud because the monkey patch from gevent was not getting applied properly on urllib3 ssl dependency.
- changelog:
    - applied monkey patch from gevent before app startup.
    - change on service command to not start up the gunicorn process inside the app context.
    - change on health endpoint so by default is unhealthy.
    - adjusted health endpoint unit and integration tests.
    - fixed version of cornflow-client to 1.0.11


version 1.0.1
---------------

- released: 2023-03-16
- description: fixed requirements versions in order to better handle the dockerfile construction on dockerhub.
- changelog:
    - fixed version of cornflow-core to 0.1.9
    - fixed version of cornflow-client to 1.0.10

version 1.0.0
--------------

- released: 2023-03-15
- description: initial release of cornflow package
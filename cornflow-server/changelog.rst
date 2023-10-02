version 1.0.5
--------------

- released: 2023-05-04
- description: first version of cornflow without cornflow core
- changelog:
    - removed cornflow core from dependencies.
    - moved all cornflow core code to cornflow.
    - added new error handling for InternalServerErrors.
    - updated version of flask to 2.3.2 due to security reasons.
    - updated version of other libraries due to upgrade on flask version.

version 1.0.4
---------------

- released: 2023-04-21
- description: added alarms models and endpoints that can be used, change the get of all executions, better error handling and new useful methods
- changelog:
    - when performing a get of all executions the running executions get their status updated
    - improve error handling
    - add alarms models and endpoints so they can be used on `external_apps`
    - added new useful methods



version 1.0.3
---------------


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
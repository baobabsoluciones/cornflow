version 1.0.9
--------------

- released: 2023-12-27
- description: added new authentication for BI endpoints where the token does not expire
- changelog:
    - Added new auth method.
    - Added new token generation that can be used only through the cli.
    - Added new token decodification that doe snot check for expiry date on token.

version 1.0.8
--------------

- released: 2023-10-20
- description: new version of cornflow with new features and bug fixes.
- changelog:
    - This version of cornflow is only compatible with Python versions 3.8 or higher, with the desired version for deployment being Python version 3.10 (preferred version for baobab development as well).
    - This version of cornflow updates the version of airflow to 2.7.1.
    - Almost all library versions have been fixed to avoid dependency problems in future deployments.
    - In the ApplicationCore you can define a new class-level argument (like schemas) which is notify. This argument, when True, automatically adds a callback that will send us an email with the log attached in case the model fails when running in Airflow.
    - There is a new default DAG (run_deployed_models) that allows us to automatically launch all the models that we have deployed and for which we have defined a test instance in the ApplicationCore definition, so that once deployed we can do a quick test of the correct functioning of the model.
    - If we create an execution and in the configuration we have not included all the information, the default values defined in the configuration json schema are taken.
    - A command that used to convert models from an external app to jsonschemas is now disabled.


version 1.0.7
--------------

- released: 2023-10-03
- description: security version of cornflow to update vulnerability on dependency
- changelog:
    - updated version of gevent to 23.9.0.post1 due to security reasons.

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
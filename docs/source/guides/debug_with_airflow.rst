Debug your solution method
============================

When your solution method is running, you can use the airflow web interface to check what is going on with your application - if it is running or paused for example - and to see the execution logs in case of an error. In airflow, our solution method runs inside something called a DAG and so we refer to dag and solution method indistinctly.

Common errors
---------------

Update schemas in Cornflow
******************************

Note that even if your dag is running, the schemas it uses might not be up to date. If you get an error saying that the variables are not found when you try to send data to the server, you might want to check the variables saved for your dag (on the airflow interface, in “Admin” → “Variables”). If there are no variables saved, it is time to update them. To that extent, you will need to trigger the dag called ‘update_all_schemas’. You can trigger it from the page ‘update_all_schemas’ on the airflow interface. It does not take any arguments.


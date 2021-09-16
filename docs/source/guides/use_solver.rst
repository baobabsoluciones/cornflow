User your solution method
==============================

python client
-----------------

Once your dag is on the server, you can use the cornflow-client package to access it on the server: 

.. code-block:: python

    from cornflow_client import CornFlow
    from time import sleep
    from instance import Instance


    path = "C:/Users/me/path/to/my/data-file.xml”
    // Data in the schema format:
    data = Instance.from_file(path).to_dict()

    client = CornFlow("https://devsm.cornflow.baobabsoluciones.app")
    // Sign_up only the first time:
    client.sign_up(YOUR_USER_NAME, YOUR_EMAIL, YOUR_PASSWORD)
    client.login(YOUR_USER_NAME, YOUR_PASSWORD)

    instance = client.create_instance(data=data, name="test_my_project", schema="my_project")
    instance_id = instance["id"]

    execution_config = dict(
       solver="algorithm1",
       timeLimit=15,
    )

    execution = client.create_execution(instance_id, execution_config, schema="my_project")
    execution_id = execution["id"]

    while not client.get_status(execution_id)["state"]:
       sleep(2)
       print("Still waiting for the solution!")
    print(client.get_status(execution_id))

    solution = client.get_solution(execution_id)
    print(solution)

    log = client.get_log(execution_id)
    print(log)


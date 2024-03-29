from cornflow_client import CornFlow

email = "some_email@gmail.com"
pwd = "some_password"
name = "some_name"


def run_example():
    server = "http://127.0.0.1:5000"
    client = CornFlow(url=server)

    config = dict(email=email, pwd=pwd, name=name)
    a = client.sign_up(**config)
    a = client.login(email, pwd)

    import pulp

    prob = pulp.LpProblem("test_export_dict_MIP", pulp.LpMinimize)
    x = pulp.LpVariable("x", 0, 4)
    y = pulp.LpVariable("y", -1, 1)
    z = pulp.LpVariable("z", 0, None, pulp.LpInteger)
    prob += x + 4 * y + 9 * z, "obj"
    prob += x + y <= 5, "c1"
    prob += x + z >= 10, "c2"
    prob += -y + z == 7.5, "c3"
    data = prob.toDict()
    filename = "test_mps.mps"
    insName = "test_export_dict_MIP"
    description = "very small example"

    instance = client.create_instance(data, name=insName, description=description)
    # alternatively: send file
    prob.writeMPS(filename=filename)
    instance = client.create_instance_file(
        filename=filename, name=insName, description=description
    )

    # edit the instance to give it a new name
    client.put_api_for_id("instance/", instance["id"], dict(name="newName"))

    # get info from an instance
    info = client.get_one_instance(instance["id"])
    # get all instances
    info_all = client.get_all_instances()

    # send an execution
    config = dict(solver="PULP_CBC_CMD", timeLimit=10)
    execution = client.create_execution(
        instance["id"],
        config,
        name="execution1",
        description="execution of a very small instance",
    )

    # check the status of the execution
    status = client.get_status(execution["id"])
    print(status["state"])
    # get the execution solution
    results = client.get_solution(execution["id"])
    _vars, prob = pulp.LpProblem.from_dict(results["data"])

    # get the values for the variables:
    print({k: v.value() for k, v in _vars.items()})

    # get the log in json format
    log = client.get_log(execution["id"])
    print(log["log"])
    # a json version of the log


def example_migrate_execution():
    email = "airflow_test@admin.com"
    pwd = "airflow_test_password"
    server = "http://127.0.0.1:5000"
    client = CornFlow(url=server)
    a = client.login(email, pwd)
    info_all = client.get_all_instances()
    instance = info_all[-1]
    info = client.get_one_instance(instance["id"])
    inst_data = client.get_api_for_id("instance/", instance["id"], "data")
    inst_data = inst_data.json()
    execution = info["executions"][-1]
    results = client.get_solution(execution["id"])
    log = client.get_log(execution["id"])

    # now we go to the other server:
    server2 = "SOME_OTHER_SERVER"
    client2 = CornFlow(url=server2)
    client2.login("ADMIN_USER", "ADMIN_PASS")

    # create instance in another server
    instance2 = client2.create_instance(
        inst_data["data"], name=info["name"], description=info["description"]
    )
    execution_new = client.manual_execution(
        instance_id=instance2["id"],
        config=execution["config"],
        name=execution["name"],
        data=results["data"],
        log_json=log["log"],
    )


if __name__ == "__main__":
    run_example()

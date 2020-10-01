from cornflow_client import CornFlow, group_variables_by_name
import pulp

email = 'some_email@gmail.com'
pwd = 'some_password'
name = 'some_name'

def run_example():

    config = dict(email=email, pwd=pwd, name=name)

    # client = CornFlow(url="http://127.0.0.1:5000")
    client = CornFlow(url="http://34.78.205.34:5000/")
    client.sign_up(**config)
    client.login(email, pwd)

    prob = build_pulp_problem()
    # The problem data is written to an .lp file
    data = prob.to_dict()

    instance_id = client.create_instance(data)

    config = dict(
        solver="PULP_CBC_CMD",
        mip=True,
        msg=True,
        warmStart=True,
        timeLimit=10,
        options=["donotexist", "thisdoesnotexist"],
        keepFiles=0,
        gapRel=0.1,
        gapAbs=1,
        threads=1,
        logPath="test_export_solver_json.log"
    )

    execution_id = client.create_execution(instance_id, config)
    status = client.get_status(execution_id)
    results = client.get_results(execution_id)

    _vars, prob = pulp.LpProblem.from_dict(results['execution_results'])
    actual_vars = group_variables_by_name(_vars, ['Route', 'BuildaPlant'], replace_underscores_with_spaces=True)
    actual_vars.keys()
    actual_vars['BuildaPlant']
    actual_vars['Route'][('San Francisco', 'Barstow')]

    # The status of the solution is printed to the screen
    print("Status:", pulp.LpStatus[prob.status])

    # Each of the variables is printed with it's resolved optimum value
    for v in prob.variables():
        print(v.name, "=", v.varValue)

    # The optimised objective function value is printed to the screen
    print("Total Cost of Transportation = ", pulp.value(prob.objective))

    # get the values for the variables:
    {k: v.value() for k, v in _vars.items()}

    # get the log in text format
    results['log_text']

    # get the log in json format
    results['log_json']


def build_pulp_problem():
    # Creates a list of all the supply nodes
    Plants = ["San Francisco",
              "Los Angeles",
              "Phoenix",
              "Denver"]

    # Creates a dictionary of lists for the number of units of supply at
    # each plant and the fixed cost of running each plant
    supplyData = {  # Plant     Supply  Fixed Cost
        "San Francisco": [1700, 70000],
        "Los Angeles": [2000, 70000],
        "Phoenix": [1700, 65000],
        "Denver": [2000, 70000]
    }

    # Creates a list of all demand nodes
    Stores = ["San Diego",
              "Barstow",
              "Tucson",
              "Dallas"]

    # Creates a dictionary for the number of units of demand at each store
    demand = {  # Store    Demand
        "San Diego": 1700,
        "Barstow": 1000,
        "Tucson": 1500,
        "Dallas": 1200
    }

    # Creates a list of costs for each transportation path
    costs = [  # Stores
        # SD BA TU DA
        [5, 3, 2, 6],  # SF
        [4, 7, 8, 10],  # LA    Plants
        [6, 5, 3, 8],  # PH
        [9, 8, 6, 5]  # DE
    ]

    # Creates a list of tuples containing all the possible routes for transport
    Routes = [(p, s) for p in Plants for s in Stores]

    # Splits the dictionaries to be more understandable
    (supply, fixedCost) = pulp.splitDict(supplyData)

    # The cost data is made into a dictionary
    costs = pulp.makeDict([Plants, Stores], costs, 0)

    plants_stores = [(p, s) for p in Plants for s in Stores]

    # Creates the problem variables of the Flow on the Arcs
    flow = pulp.LpVariable.dicts("Route", plants_stores, 0, None, pulp.LpInteger)

    # Creates the master problem variables of whether to build the Plants or not
    build = pulp.LpVariable.dicts("BuildaPlant", Plants, 0, 1, pulp.LpInteger)

    # Creates the 'prob' variable to contain the problem data
    prob = pulp.LpProblem("Computer Plant Problem", pulp.LpMinimize)

    # The objective function is added to prob - The sum of the transportation costs and the building fixed costs
    prob += pulp.lpSum([flow[p, s] * costs[p][s] for (p, s) in Routes]) + pulp.lpSum(
        [fixedCost[p] * build[p] for p in Plants]), "Total Costs"

    # The Supply maximum constraints are added for each supply node (plant)
    for p in Plants:
        prob += pulp.lpSum([flow[p, s] for s in Stores]) <= supply[p] * build[p], "Sum of Products out of Plant %s" % p

    # The Demand minimum constraints are added for each demand node (store)
    for s in Stores:
        prob += pulp.lpSum([flow[p, s] for p in Plants]) >= demand[s], "Sum of Products into Stores %s" % s

    return prob

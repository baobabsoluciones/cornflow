from airflow import DAG
from airflow.operators.python import PythonVirtualenvOperator
from datetime import datetime, timedelta

# Following are defaults which can be overridden later on
# TODO: clean this
default_args = {
    'owner': 'hugo',
    'depends_on_past': False,
    'start_date': datetime(2020, 2, 1),
    'email': [''],
    'email_on_failure': False,
    'email_on_retry': False,
    'retry_delay': timedelta(minutes=1),
    'schedule_interval': None
}

dag1 = DAG('hk_2020_dag_venv', default_args=default_args, schedule_interval=None)

def hk_in_venv(**kwargs):

    from hackathonbaobab2020 import get_solver
    from hackathonbaobab2020.core import Instance
    from hackathonbaobab2020.core.tools import dict_to_list
    from timeit import default_timer as timer

    def get_arg(arg, context):
        return context["dag_run"].conf[arg]
    
    def solve_from_dict(data, solver_name, options):
        """
        :param data: json for the problem
        :param solver_name: solver to use
        :param options: options
        :return: solution and log
        """
        print("Solving the model")
        print(solver_name)
        solver = get_solver(solver_name)
        print(data)
        inst = Instance.from_dict(data)
        algo = solver(inst)
        start = timer()
    
        try:
            status = algo.solve(options)
            print("ok")
        except Exception as e:
            print(e)
            status = 0
    
        if status != 0:
            # export everything:
            status_conv = {4: "Optimal", 2: "Feasible", 3: "Infeasible", 0: "Unknown"}
            log = dict(time=timer() - start, solver=solver_name, status=status_conv.get(status, "Unknown"))
            sol = dict_to_list(algo.solution.data, 'job')
        else:
            log = "error"
            sol = {}
    
        return sol, log

    def test_hk(**kwargs):
        data = get_arg("data", kwargs)
        print(data)
        solver_name = get_arg("solver", kwargs)
        options = get_arg("options", kwargs)
    
        return solve_from_dict(data, solver_name, options)
    
    return test_hk(**kwargs)

#
# hackaton_task_venv = PythonVirtualenvOperator(
#     task_id='hk_2020_task_venv',
#     python_callable=hk_in_venv,
#     requirements= ["hackathonbaobab2020", "timeit"],
#     python_version = 3.8,
#     system_site_packages=True,
#     dag=dag1
# )



    
    
    
    
    
    
    
    
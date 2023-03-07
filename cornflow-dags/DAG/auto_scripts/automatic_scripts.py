import os
import shutil

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Default arguments of DAG
default_args = {
    "owner": "baobab",
    "depends_on_past": False,
    "start_date": datetime(2023, 1, 1),
    "email": [""],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": -1,
    "retry_delay": timedelta(minutes=1),
    "catchup": False,
}
# Folder path
CONN = os.environ.get("CORNFLOW_DB_URI", "NA")


def move_script(script_folder, destination_folder, auto_script, log="", error=0):
    # Get current date and time
    now = datetime.now()

    # Format date and time as string
    datetime_str = now.strftime("%Y%m%d_%H%M")

    # Name of folder to create. If the script had an error, the name of the folder flags it
    if error:
        folder_name = f"ERROR_{os.path.splitext(auto_script)[0]}_{datetime_str}"
    else:
        folder_name = f"{os.path.splitext(auto_script)[0]}_{datetime_str}"

    # Full path of folder to create
    folder_path = os.path.join(destination_folder, folder_name)

    # Create folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
        print(f"Folder created successfully at {folder_path}")
    else:
        print(f"Folder '{folder_path}' already exists.")

    # Move script to folder
    script_path = os.path.join(script_folder, auto_script)
    shutil.move(script_path, folder_path)
    # Export log
    log_path = os.path.join(folder_path, "log.txt")
    with open(log_path, "w") as file:
        # Write log
        file.write(log)
    print(f"Script {auto_script} moved out of folder")


def execute_scripts(
    script_folder="/usr/local/airflow/dags/auto_scripts/scripts_to_execute",
    destination_folder="/usr/local/airflow/dags/auto_scripts/executed_scripts",
):

    # Iterate directory
    for auto_script in os.listdir(script_folder):
        error = 0
        print(f"Executing {auto_script}")
        # Check if current path is a file
        if os.path.isfile(os.path.join(script_folder, auto_script)):
            script_path = os.path.join(script_folder, auto_script)

            # Check if python file
            if ".py" in auto_script:
                error = os.system(f"python {script_path} > output.txt 2>&1")

                with open("output.txt", "r") as f:
                    log = f.read()

                os.remove("output.txt")

                if error != 0:
                    print(f"Something went wrong: {str(log)}")
                else:
                    print(f"Script executed successfully: {str(log)}")

            elif ".sql" in auto_script:
                log = ""
                # Read the SQL file
                with open(script_path, "r") as f:
                    query = f.read()

                try:
                    # Connect to the database
                    engine = create_engine(CONN)

                except Exception as e:
                    # Print the error message
                    if CONN == "NA":
                        message = "If there is no database connection no queries can be performed"
                        print(message)
                        log += str(e)
                    else:
                        print(f"Error: {e}")
                        log += str(e)
                    error = 1
                    move_script(
                        script_folder, destination_folder, auto_script, log, error
                    )
                    continue

                # All SQL commands (split on ';')
                sqlCommands = query.split(";")
                for command in sqlCommands:
                    # Check empty query
                    if command == "":
                        continue
                    # Begin a transaction
                    with engine.connect() as connection:
                        transaction = connection.begin()
                        try:
                            # Execute the SQL query
                            print(f"Query: {command}")
                            connection.execute(command)
                            # Commit the transaction
                            transaction.commit()
                            message = "Query executed successfully!"
                            log += message
                            print(message)

                        except SQLAlchemyError as e:
                            # Rollback the transaction if the query is not successful
                            transaction.rollback()

                            # Print the error message
                            print(f"Error: {e}")
                            log += str(e)
                            error = 1

            else:
                print(
                    f"The script {auto_script} is not recognized as either a python file or a sql file"
                )
                # We do nothing with the file
                continue
            # Move script and create log
            move_script(script_folder, destination_folder, auto_script, log, error)
            print(f"End of {auto_script} execution.")
        else:
            print(f"{auto_script} is not a file")

    return 200


dag = DAG(
    "execute_scripts",
    default_args=default_args,
    catchup=False,
    tags=["internal"],
    schedule_interval="@hourly",
)

execute_scripts2 = PythonOperator(
    task_id="execute_scripts",
    provide_context=True,
    python_callable=execute_scripts,
    dag=dag,
)


if __name__ == "__main__":
    execute_scripts()

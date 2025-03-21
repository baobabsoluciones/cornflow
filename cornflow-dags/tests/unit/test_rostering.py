import os
from datetime import datetime, timedelta

from cornflow_client.core.tools import load_json

from tests.unit.test_dags import BaseDAGTests


class RosteringTestCase(BaseDAGTests.SolvingTests):
    def setUp(self):
        super().setUp()
        from DAG.rostering import Rostering

        self.app = Rostering()
        self.config.update(dict(solver="mip.PULP_CBC_CMD", rel_gap=0.02))

    def test_incoherent_timeslot_length(self):
        """
        Test that the timeslot length is incoherent
        """
        super().setUp()
        from DAG.rostering import Rostering

        app = Rostering()

        instance_data = load_json(
            os.path.join(
                os.path.dirname(__file__),
                "../../DAG/rostering/data/test_instance_bad_timeslot_length.json",
            )
        )

        _, _, instance_checks, _, _ = app.solve(instance_data, self.config, None)

        self.assertEqual(instance_checks, {"timeslot_length": 120})

    def test_incoherent_foreign_keys(self):
        """
        Test that the foreign keys are incoherent
        """
        super().setUp()
        from DAG.rostering import Rostering

        app = Rostering()

        # Create test data with an incoherent foreign key
        # Start with a valid instance
        instance_data = load_json(
            os.path.join(
                os.path.dirname(__file__),
                "../../DAG/rostering/data/test_instance_1.json",
            )
        )

        # Modify the data to create an incoherent foreign key
        # Add a contract with a non-existent employee ID
        non_existent_employee_id = 999

        # Copy an existing contract and modify it to use a non-existent employee ID
        if len(instance_data["contracts"]) > 0:
            new_contract = dict(instance_data["contracts"][0])
            new_contract["id"] = max(c["id"] for c in instance_data["contracts"]) + 1
            new_contract["id_employee"] = non_existent_employee_id
            instance_data["contracts"].append(new_contract)
        else:
            # If no contracts exist, create a basic one
            new_contract = {
                "id": 1,
                "id_employee": non_existent_employee_id,
                "id_shift": 1,
                "start_contract": "2023-01-01",
                "end_contract": "2023-12-31",
                "weekly_hours": 40,
                "days_worked": 5,
            }
            instance_data["contracts"].append(new_contract)

        # Run the solver
        _, _, instance_checks, _, _ = app.solve(instance_data, self.config, None)

        # Verify the results
        self.assertIn("incoherent_foreign_keys", instance_checks)
        self.assertTrue(len(instance_checks["incoherent_foreign_keys"]) > 0)

        # Find the specific error we created
        found_error = False
        for error in instance_checks["incoherent_foreign_keys"]:
            if (
                error["primary_table"] == "employees"
                and error["foreign_table"] == "contracts"
                and error["key"] == "id_employee"
                and error["value"] == non_existent_employee_id
            ):
                found_error = True
                break

        self.assertTrue(
            found_error, "Expected error for non-existent employee ID was not found"
        )

    def test_missing_data(self):
        """
        Test that missing data relationships are detected
        """
        super().setUp()
        from DAG.rostering import Rostering

        app = Rostering()

        # Create test data with missing required data
        # Start with a valid instance
        instance_data = load_json(
            os.path.join(
                os.path.dirname(__file__),
                "../../DAG/rostering/data/test_instance_1.json",
            )
        )

        # Add a new employee without creating a corresponding contract
        # (contracts are required for employees as per INSTANCE_KEYS_RELATION)
        new_employee_id = max(e["id"] for e in instance_data["employees"]) + 1

        # Create a new employee
        new_employee = dict(instance_data["employees"][0])
        new_employee["id"] = new_employee_id
        new_employee["name"] = f"Test Employee {new_employee_id}"
        instance_data["employees"].append(new_employee)

        # Run the solver
        _, _, instance_checks, _, _ = app.solve(instance_data, self.config, None)

        # Verify the results
        self.assertIn("missing_data", instance_checks)
        self.assertTrue(len(instance_checks["missing_data"]) > 0)

        # Find the specific error we created
        found_error = False
        for error in instance_checks["missing_data"]:
            if (
                error["primary_table"] == "employees"
                and error["foreign_table"] == "contracts"
                and error["key"] == "id"
                and error["value"] == new_employee_id
            ):
                found_error = True
                break

        self.assertTrue(
            found_error, "Expected error for employee without contract was not found"
        )

    def test_weekly_schedule_timeslots_warning(self):
        """
        Test that warnings are generated when weekly schedule times
        are not aligned with the slot length
        """
        super().setUp()
        from DAG.rostering import Rostering

        app = Rostering()

        # Start with a valid instance
        instance_data = load_json(
            os.path.join(
                os.path.dirname(__file__),
                "../../DAG/rostering/data/test_instance_1.json",
            )
        )

        # Save the original slot length to make sure the test will work correctly
        slot_length = instance_data["parameters"]["slot_length"]

        # Ensure slot length is a divisor of 60 (assumed to be 15, 30, or 60)
        self.assertIn(slot_length, [15, 30, 60], "Test requires standard slot length")

        # Add a weekly schedule entry with minutes not divisible by the slot length
        # This won't be divisible by 15, 30 or 60
        non_aligned_minute = 5

        # Find a weekday that's not already in the weekly schedule or use a new one
        existing_weekdays = {
            entry["week_day"] for entry in instance_data["weekly_schedule"]
        }
        weekday = 1
        while weekday in existing_weekdays and weekday <= 7:
            weekday += 1

        # Create a new weekly schedule entry with non-aligned minutes
        instance_data["weekly_schedule"].append(
            {
                "week_day": weekday,
                "starting_hour": f"08:{non_aligned_minute:02d}",
                "ending_hour": "17:00",
            }
        )

        self.config.update(dict(solver="mip.PULP_CBC_CMD", rel_gap=0.02))

        # Run the solver
        _, _, instance_checks, _, _ = app.solve(instance_data, self.config, None)

        # Verify the results
        self.assertIn("weekly_schedule_timeslots", instance_checks)
        self.assertTrue(len(instance_checks["weekly_schedule_timeslots"]) > 0)

        # Find the specific warning we created
        found_warning = False
        for warning in instance_checks["weekly_schedule_timeslots"]:
            if (
                warning["weekday"] == weekday
                and warning["hour"] == f"08:{non_aligned_minute:02d}"
            ):
                found_warning = True
                break

        self.assertTrue(
            found_warning,
            f"Expected warning for non-aligned time (08:{non_aligned_minute:02d}) was not found",
        )

    def test_schedule_exceptions_timeslots_warning(self):
        """
        Test that warnings are generated when schedule exceptions times
        are not aligned with the slot length
        """
        super().setUp()
        from DAG.rostering import Rostering

        app = Rostering()

        # Start with a valid instance
        instance_data = load_json(
            os.path.join(
                os.path.dirname(__file__),
                "../../DAG/rostering/data/test_instance_1.json",
            )
        )

        # Save the original slot length to make sure the test will work correctly
        slot_length = instance_data["parameters"]["slot_length"]

        # Ensure slot length is a divisor of 60 (assumed to be 15, 30, or 60)
        self.assertIn(slot_length, [15, 30, 60], "Test requires standard slot length")

        # Add a schedule exception with minutes not divisible by the slot length
        non_aligned_minute = 5  # This won't be divisible by 15, 30 or 60

        # Use a date that's in the future to avoid conflicts
        # Create a date string in YYYY-MM-DD format for tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        # Create a new schedule exception entry with non-aligned minutes
        if "schedule_exceptions" not in instance_data:
            instance_data["schedule_exceptions"] = []

        instance_data["schedule_exceptions"].append(
            {
                "date": tomorrow,
                "starting_hour": f"08:{non_aligned_minute:02d}",  # e.g., "08:05"
                "ending_hour": "17:00",
            }
        )

        self.config.update(dict(solver="mip.PULP_CBC_CMD", rel_gap=0.02))

        # Run the solver
        _, _, instance_checks, _, _ = app.solve(instance_data, self.config, None)

        # Verify the results
        self.assertIn("schedule_exceptions_timeslots", instance_checks)
        self.assertTrue(len(instance_checks["schedule_exceptions_timeslots"]) > 0)

        # Find the specific warning we created
        found_warning = False
        for warning in instance_checks["schedule_exceptions_timeslots"]:
            if (
                warning["date"] == tomorrow
                and warning["hour"] == f"08:{non_aligned_minute:02d}"
            ):
                found_warning = True
                break

        self.assertTrue(
            found_warning,
            f"Expected warning for non-aligned time (08:{non_aligned_minute:02d}) was not found",
        )

    def test_shift_hours_timeslots_warning(self):
        """
        Test that warnings are generated when shift hours
        are not aligned with the slot length
        """
        super().setUp()
        from DAG.rostering import Rostering

        app = Rostering()

        # Start with a valid instance - use test_instance_4 which has more shifts
        instance_data = load_json(
            os.path.join(
                os.path.dirname(__file__),
                "../../DAG/rostering/data/test_instance_4.json",
            )
        )

        # Save the original slot length to make sure the test will work correctly
        slot_length = instance_data["parameters"]["slot_length"]

        # Ensure slot length is a divisor of 60 (assumed to be 15, 30, or 60)
        self.assertIn(slot_length, [15, 30, 60], "Test requires standard slot length")

        # Modify a shift to have a non-aligned starting hour
        non_aligned_minute = 5  # This won't be divisible by 15, 30 or 60

        # Choose the first shift
        if len(instance_data["shifts"]) > 0:
            # Modify its start hour to have non-aligned minutes
            instance_data["shifts"][0]["start"] = f"08:{non_aligned_minute:02d}"
            shift_id = instance_data["shifts"][0]["id"]

            self.config.update(dict(solver="mip.PULP_CBC_CMD", rel_gap=0.02))

            # Run the solver
            _, _, instance_checks, _, _ = app.solve(instance_data, self.config, None)

            # Verify the results
            self.assertIn("shift_hours_timeslots", instance_checks)
            self.assertTrue(len(instance_checks["shift_hours_timeslots"]) > 0)

            # Find the specific warning we created
            found_warning = False
            for warning in instance_checks["shift_hours_timeslots"]:
                # In the output, the "employee" field is from the contract that uses this shift
                # We just need to verify the hour matches
                if warning["hour"] == f"08:{non_aligned_minute:02d}":
                    found_warning = True
                    break

            self.assertTrue(
                found_warning,
                f"Expected warning for non-aligned shift time (08:{non_aligned_minute:02d}) was not found",
            )
        else:
            self.skipTest("No shifts found in test data to modify")

    def test_employee_preferences_timeslots_warning(self):
        """
        Test that warnings are generated when employee preferences times
        are not aligned with the slot length
        """
        super().setUp()
        from DAG.rostering import Rostering

        app = Rostering()

        # Start with a valid instance with preferences - test_instance_7
        instance_data = load_json(
            os.path.join(
                os.path.dirname(__file__),
                "../../DAG/rostering/data/test_instance_7.json",
            )
        )

        # Save the original slot length to make sure the test will work correctly
        slot_length = instance_data["parameters"]["slot_length"]

        # Ensure slot length is a divisor of 60 (assumed to be 15, 30, or 60)
        self.assertIn(slot_length, [15, 30, 60], "Test requires standard slot length")

        # Add an employee preference with minutes not divisible by the slot length
        non_aligned_minute = 5  # This won't be divisible by 15, 30 or 60

        # Make sure we have employee preferences
        if (
            "employee_preferences" not in instance_data
            or not instance_data["employee_preferences"]
        ):
            # If no preferences, we need to add one
            # Get the first employee and a valid date from the data
            if len(instance_data["employees"]) > 0:
                employee_id = instance_data["employees"][0]["id"]

                # Use the first date in the instance
                first_date = instance_data["parameters"]["starting_date"]

                # Create a preference
                instance_data["employee_preferences"] = [
                    {
                        "id_employee": employee_id,
                        "day": first_date,
                        "hours": 8,
                        "start": f"08:{non_aligned_minute:02d}",
                    }
                ]
            else:
                self.skipTest("No employees found in test data")
        else:
            # Modify an existing preference
            instance_data["employee_preferences"][0][
                "start"
            ] = f"08:{non_aligned_minute:02d}"
            employee_id = instance_data["employee_preferences"][0]["id_employee"]
            day = instance_data["employee_preferences"][0]["day"]

        self.config.update(dict(solver="mip.PULP_CBC_CMD", rel_gap=0.02))

        # Run the solver
        _, _, instance_checks, _, _ = app.solve(instance_data, self.config, None)

        # Verify the results
        self.assertIn("employee_preferences_timeslots", instance_checks)
        self.assertTrue(len(instance_checks["employee_preferences_timeslots"]) > 0)

        # Find the specific warning we created
        found_warning = False
        for warning in instance_checks["employee_preferences_timeslots"]:
            # The schema defines the field as "employee", "date", and "hour"
            if warning["hour"] == f"08:{non_aligned_minute:02d}":
                found_warning = True
                break

        self.assertTrue(
            found_warning,
            f"Expected warning for non-aligned preference time (08:{non_aligned_minute:02d}) was not found",
        )

    def test_fixed_worktable_timeslots_warning(self):
        """
        Test that warnings are generated when fixed worktable times
        are not aligned with the slot length
        """
        super().setUp()
        from DAG.rostering import Rostering

        app = Rostering()

        # Start with a valid instance
        instance_data = load_json(
            os.path.join(
                os.path.dirname(__file__),
                "../../DAG/rostering/data/test_instance_1.json",
            )
        )

        # Save the original slot length to make sure the test will work correctly
        slot_length = instance_data["parameters"]["slot_length"]

        # Ensure slot length is a divisor of 60 (assumed to be 15, 30, or 60)
        self.assertIn(slot_length, [15, 30, 60], "Test requires standard slot length")

        # Add a fixed worktable with minutes not divisible by the slot length
        non_aligned_minute = 5  # This won't be divisible by 15, 30 or 60

        # Create the fixed_worktables entry if it doesn't exist
        if "fixed_worktables" not in instance_data:
            instance_data["fixed_worktables"] = []

        # Get the first employee ID
        employee_id = instance_data["employees"][0]["id"]

        # Use the first date in the instance
        first_date = instance_data["parameters"]["starting_date"]

        # Create a fixed worktable entry with non-aligned minutes
        instance_data["fixed_worktables"].append(
            {
                "id_employee": employee_id,
                "date": first_date,
                "hour": f"08:{non_aligned_minute:02d}",
            }
        )

        self.config.update(dict(solver="mip.PULP_CBC_CMD", rel_gap=0.02))

        # Run the solver
        _, _, instance_checks, _, _ = app.solve(instance_data, self.config, None)

        # Verify the results
        self.assertIn("fixed_worktable_timeslots", instance_checks)
        self.assertTrue(len(instance_checks["fixed_worktable_timeslots"]) > 0)

        # Find the specific warning we created
        found_warning = False
        for warning in instance_checks["fixed_worktable_timeslots"]:
            if (
                warning["employee"] == employee_id
                and warning["date"] == first_date
                and warning["hour"] == f"08:{non_aligned_minute:02d}"
            ):
                found_warning = True
                break

        self.assertTrue(
            found_warning,
            f"Expected warning for non-aligned fixed worktable time (08:{non_aligned_minute:02d}) was not found",
        )

    def test_penalties_warning(self):
        """
        Test that warnings are generated when penalties are missing for soft constraints
        """
        super().setUp()
        from DAG.rostering import Rostering

        app = Rostering()

        # Start with instance 8 which has everything but deactivated
        instance_data = load_json(
            os.path.join(
                os.path.dirname(__file__),
                "../../DAG/rostering/data/test_instance_8.json",
            )
        )

        # Find a requirement that is set to "soft" but doesn't have a penalty
        # First, set a requirement to "soft"
        found_req = None
        for req, value in instance_data["requirements"].items():
            if value != "soft":
                instance_data["requirements"][req] = "soft"
                found_req = req
                break

        if not found_req:
            # If we didn't find a non-soft requirement, just use the first one
            found_req = list(instance_data["requirements"].keys())[0]
            instance_data["requirements"][found_req] = "soft"

        # Now remove its penalty if it exists
        if found_req in instance_data["penalties"]:
            del instance_data["penalties"][found_req]

        self.config.update(dict(solver="mip.PULP_CBC_CMD", rel_gap=0.02))

        # Run the solver
        _, _, instance_checks, _, _ = app.solve(instance_data, self.config, None)

        # Verify the results
        self.assertIn("penalties", instance_checks)
        self.assertTrue(len(instance_checks["penalties"]) > 0)

        # Find the specific warning we created
        found_warning = False
        for warning in instance_checks["penalties"]:
            if warning["requirement"] == found_req:
                found_warning = True
                break

        self.assertTrue(
            found_warning,
            f"Expected warning for missing penalty for requirement {found_req} was not found",
        )

import io
import os
import tempfile
import unittest
import zipfile
from unittest.mock import Mock, patch

from cornflow_client import (
    ApplicationCore,
    CornFlow,
    ExperimentCore,
    InstanceCore,
    SolutionCore,
    get_empty_schema,
)
from cornflow_client.constants import (
    EXECUTION_FILES_STATUS_ERROR,
    EXECUTION_FILES_STATUS_NOT_GENERATED,
    EXECUTION_FILES_STATUS_OK,
    SOLUTION_STATUS_FEASIBLE,
    STATUS_OPTIMAL,
)
from cornflow_client.raw_cornflow_client import CornFlowApiError, RawCornFlow


class ExecutionFilesInstance(InstanceCore):
    schema = get_empty_schema()
    schema_checks = get_empty_schema()


class ExecutionFilesSolution(SolutionCore):
    schema = get_empty_schema()


class ExecutionFilesExperiment(ExperimentCore):
    schema_checks = get_empty_schema()

    def __init__(self, instance, solution=None, output_files=None):
        super().__init__(instance, solution)
        self.output_files = output_files

    def solve(self, options):
        return {}

    def get_objective(self):
        return 0

    def generate_output_files(
        self, instance_checks, instance_has_errors, solution_checks, solution_has_errors
    ):
        return self.output_files


class TestRawCornflowExecutionFiles(unittest.TestCase):
    def setUp(self):
        self.client = RawCornFlow(url="http://cornflow.test/", token="token")

    @patch.object(RawCornFlow, "post_api_for_id")
    def test_write_execution_files_with_status_only(self, post_api_for_id):
        """
        Validates that RawCornFlow posts only status data when no zip is supplied.
        """
        self.client.write_execution_files(
            execution_id="execution-id",
            execution_files_status=EXECUTION_FILES_STATUS_ERROR,
        )

        post_api_for_id.assert_called_once_with(
            "execution/files/",
            id="execution-id",
            data={"execution_files_status": EXECUTION_FILES_STATUS_ERROR},
        )

    @patch.object(RawCornFlow, "post_api_for_id")
    def test_write_execution_files_preserves_status_value(self, post_api_for_id):
        """
        Validates that RawCornFlow passes execution file statuses through unchanged.
        """
        self.client.write_execution_files(
            execution_id="execution-id",
            execution_files_status="custom-status",
        )

        post_api_for_id.assert_called_once_with(
            "execution/files/",
            id="execution-id",
            data={"execution_files_status": "custom-status"},
        )

    @patch.object(RawCornFlow, "post_api_for_id")
    def test_write_execution_files_with_zip(self, post_api_for_id):
        """
        Validates that RawCornFlow sends execution zips as multipart upload tuples.
        """
        zip_file = io.BytesIO(b"zip-content")

        self.client.write_execution_files(
            execution_id="execution-id",
            execution_files_status=EXECUTION_FILES_STATUS_OK,
            execution_file=zip_file,
        )

        post_api_for_id.assert_called_once_with(
            "execution/files/",
            id="execution-id",
            data={"execution_files_status": EXECUTION_FILES_STATUS_OK},
            files={"execution_file": ("execution.zip", zip_file, "application/zip")},
        )

    def test_write_execution_files_requires_token(self):
        """
        Validates that RawCornFlow requires authentication before writing files.
        """
        client = RawCornFlow(url="http://cornflow.test/")

        with self.assertRaises(CornFlowApiError):
            client.write_execution_files(
                execution_id="execution-id",
                execution_files_status=EXECUTION_FILES_STATUS_ERROR,
            )


class TestCornflowExecutionFiles(unittest.TestCase):
    @patch.object(RawCornFlow, "write_execution_files")
    def test_write_execution_files_returns_json_on_success(
        self, raw_write_execution_files
    ):
        """
        Validates that CornFlow unwraps successful execution-files responses as JSON.
        """
        response = Mock(status_code=200)
        response.json.return_value = {"message": "files saved"}
        raw_write_execution_files.return_value = response

        client = CornFlow(url="http://cornflow.test/", token="token")
        result = client.write_execution_files(
            execution_id="execution-id",
            execution_files_status=EXECUTION_FILES_STATUS_ERROR,
        )

        self.assertEqual({"message": "files saved"}, result)
        raw_write_execution_files.assert_called_once_with(
            execution_id="execution-id",
            execution_files_status=EXECUTION_FILES_STATUS_ERROR,
        )

    @patch.object(RawCornFlow, "write_execution_files")
    def test_write_execution_files_raises_on_unexpected_status(
        self, raw_write_execution_files
    ):
        """
        Validates that CornFlow raises when execution-files writes return non-200.
        """
        response = Mock(status_code=500, text="server error")
        raw_write_execution_files.return_value = response

        client = CornFlow(url="http://cornflow.test/", token="token")

        with self.assertRaisesRegex(
            CornFlowApiError, "Expected a code 200.*server error"
        ):
            client.write_execution_files(
                execution_id="execution-id",
                execution_files_status=EXECUTION_FILES_STATUS_ERROR,
            )


class TestExperimentExecutionFiles(unittest.TestCase):
    def _experiment(self, output_files=None):
        instance = ExecutionFilesInstance({"items": [{"id": 1, "value": 2}]})
        solution = ExecutionFilesSolution({"assignments": [{"id": 1, "selected": 1}]})
        return ExecutionFilesExperiment(instance, solution, output_files=output_files)

    @staticmethod
    def _zip_names(zip_file):
        with zipfile.ZipFile(zip_file) as zf:
            return [name.replace("\\", "/") for name in zf.namelist()]

    def test_generate_zip_file_accepts_streams_files_and_directories(self):
        """
        Validates zip generation from byte streams, text streams, files, and folders.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "result.txt")
            with open(file_path, "w") as fd:
                fd.write("file output")

            folder_path = os.path.join(temp_dir, "folder")
            os.mkdir(folder_path)
            nested_path = os.path.join(folder_path, "nested.txt")
            with open(nested_path, "w") as fd:
                fd.write("nested output")

            zip_file = ExecutionFilesExperiment._generate_zip_file(
                {
                    "/streams/bytes.txt": io.BytesIO(b"bytes output"),
                    "streams/text.txt": io.StringIO("text output"),
                    "files/result.txt": file_path,
                    "folder": folder_path,
                }
            )

            with zipfile.ZipFile(zip_file) as zf:
                names = [name.replace("\\", "/") for name in zf.namelist()]
                self.assertIn("streams/bytes.txt", names)
                self.assertIn("streams/text.txt", names)
                self.assertIn("files/result.txt", names)
                self.assertIn("folder/nested.txt", names)
                self.assertEqual(b"bytes output", zf.read("streams/bytes.txt"))
                self.assertEqual(b"text output", zf.read("streams/text.txt"))

    def test_generate_zip_file_strips_leading_backslash(self):
        """
        Validates that leading backslashes are stripped from zip member names.
        """
        zip_file = ExecutionFilesExperiment._generate_zip_file(
            {"\\streams\\text.txt": io.StringIO("text output")}
        )

        self.assertIn("streams/text.txt", self._zip_names(zip_file))

    def test_get_zip_file_returns_not_generated_without_output_files(self):
        """
        Validates that no custom output files maps to NOT_GENERATED and no zip.
        """
        zip_file, status = self._experiment()._get_zip_file({}, False, {}, False)

        self.assertIsNone(zip_file)
        self.assertEqual(EXECUTION_FILES_STATUS_NOT_GENERATED, status)

    def test_get_zip_file_includes_custom_and_default_files(self):
        """
        Validates that generated zips include custom files and default Excel exports.
        """
        experiment = self._experiment(
            output_files={"custom/output.txt": io.StringIO("custom output")}
        )

        zip_file, status = experiment._get_zip_file(
            {"checks": [{"id": 1}]}, False, {"solution_checks": [{"id": 2}]}, False
        )

        self.assertEqual(EXECUTION_FILES_STATUS_OK, status)
        names = self._zip_names(zip_file)
        self.assertIn("custom/output.txt", names)
        self.assertIn("instance.xlsx", names)
        self.assertIn("solution.xlsx", names)
        self.assertIn("checks.xlsx", names)
        self.assertIn("solution_checks.xlsx", names)

    def test_get_zip_file_includes_default_kpis_file(self):
        """
        Validates that KPI data is included as a default Excel export.
        """
        experiment = self._experiment(output_files={})
        experiment.kpis = {"summary": [{"value": 1}]}

        zip_file, status = experiment._get_zip_file({}, False, {}, False)

        self.assertEqual(EXECUTION_FILES_STATUS_OK, status)
        self.assertIn("kpis.xlsx", self._zip_names(zip_file))

    def test_get_zip_file_cleans_path_outputs_after_zipping(self):
        """
        Validates that temporary file outputs are removed after zip generation.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "temporary-output.txt")
            with open(file_path, "w") as fd:
                fd.write("temporary output")

            experiment = self._experiment(
                output_files={"custom/temporary-output.txt": file_path}
            )

            zip_file, status = experiment._get_zip_file({}, False, {}, False)

            self.assertEqual(EXECUTION_FILES_STATUS_OK, status)
            self.assertIn("custom/temporary-output.txt", self._zip_names(zip_file))
            self.assertFalse(os.path.exists(file_path))

    def test_get_zip_file_cleans_directory_outputs_after_zipping(self):
        """
        Validates that temporary directory outputs are removed after zip generation.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            folder_path = os.path.join(temp_dir, "temporary-folder")
            os.mkdir(folder_path)
            nested_path = os.path.join(folder_path, "nested.txt")
            with open(nested_path, "w") as fd:
                fd.write("temporary output")

            experiment = self._experiment(output_files={"custom/folder": folder_path})

            zip_file, status = experiment._get_zip_file({}, False, {}, False)

            self.assertEqual(EXECUTION_FILES_STATUS_OK, status)
            self.assertIn("custom/folder/nested.txt", self._zip_names(zip_file))
            self.assertFalse(os.path.exists(folder_path))

    def test_get_zip_file_returns_error_when_generation_fails(self):
        """
        Validates that unsupported output file items return ERROR and no zip.
        """
        zip_file, status = self._experiment(
            output_files={"bad": object()}
        )._get_zip_file({}, False, {}, False)

        self.assertIsNone(zip_file)
        self.assertEqual(EXECUTION_FILES_STATUS_ERROR, status)

    def test_get_zip_file_returns_error_when_output_generation_raises(self):
        """
        Validates that generate_output_files exceptions return ERROR and no zip.
        """
        class FailingOutputExperiment(ExecutionFilesExperiment):
            def generate_output_files(
                self,
                instance_checks,
                instance_has_errors,
                solution_checks,
                solution_has_errors,
            ):
                raise RuntimeError("output failed")

        zip_file, status = FailingOutputExperiment(
            self._experiment().instance, self._experiment().solution
        )._get_zip_file({}, False, {}, False)

        self.assertIsNone(zip_file)
        self.assertEqual(EXECUTION_FILES_STATUS_ERROR, status)

    def test_get_zip_file_returns_error_when_default_generation_raises(self):
        """
        Validates that default output file generation failures return ERROR and no zip.
        """
        experiment = self._experiment(output_files={})

        with patch.object(
            experiment, "_get_default_output_files", side_effect=RuntimeError("default")
        ):
            zip_file, status = experiment._get_zip_file({}, False, {}, False)

        self.assertIsNone(zip_file)
        self.assertEqual(EXECUTION_FILES_STATUS_ERROR, status)

    def test_get_zip_file_returns_error_when_zipping_raises(self):
        """
        Validates that zip creation failures return ERROR and no zip.
        """
        experiment = self._experiment(
            output_files={"custom/output.txt": io.StringIO("x")}
        )

        with patch.object(
            ExecutionFilesExperiment,
            "_generate_zip_file",
            side_effect=RuntimeError("zip"),
        ):
            zip_file, status = experiment._get_zip_file({}, False, {}, False)

        self.assertIsNone(zip_file)
        self.assertEqual(EXECUTION_FILES_STATUS_ERROR, status)


class ApplicationExecutionFilesSolver(ExecutionFilesExperiment):
    output_files = None

    def solve(self, options):
        self.solution = ExecutionFilesSolution(
            {"assignments": [{"id": 1, "selected": 1}]}
        )
        return {
            "status": STATUS_OPTIMAL,
            "status_sol": SOLUTION_STATUS_FEASIBLE,
        }

    def generate_output_files(
        self, instance_checks, instance_has_errors, solution_checks, solution_has_errors
    ):
        return type(self).output_files


class ExecutionFilesApplication(ApplicationCore):
    name = "execution-files"
    instance = ExecutionFilesInstance
    solution = ExecutionFilesSolution
    solvers = {"default": ApplicationExecutionFilesSolver}
    schema = get_empty_schema({}, solvers=["default"])
    test_cases = []


class TestApplicationExecutionFiles(unittest.TestCase):
    def setUp(self):
        self.app = ExecutionFilesApplication()
        self.instance_data = {"items": [{"id": 1, "value": 2}]}
        self.solution_data = {"assignments": [{"id": 1, "selected": 1}]}
        self.config = {"solver": "default", "msg": False}

    def tearDown(self):
        ApplicationExecutionFilesSolver.output_files = None

    def test_solve_propagates_not_generated_zip_status(self):
        """
        Validates that solve propagates NOT_GENERATED when no output files exist.
        """
        ApplicationExecutionFilesSolver.output_files = None

        result = self.app.solve(self.instance_data, self.config)

        self.assertIsNone(result[4])
        self.assertEqual(EXECUTION_FILES_STATUS_NOT_GENERATED, result[5])

    def test_solve_propagates_successful_zip(self):
        """
        Validates that solve propagates the generated zip and OK status.
        """
        ApplicationExecutionFilesSolver.output_files = {
            "custom/output.txt": io.StringIO("output")
        }

        result = self.app.solve(self.instance_data, self.config)

        self.assertIsNotNone(result[4])
        self.assertEqual(EXECUTION_FILES_STATUS_OK, result[5])
        self.assertIn(
            "custom/output.txt", TestExperimentExecutionFiles._zip_names(result[4])
        )

    def test_solve_propagates_zip_generation_error(self):
        """
        Validates that solve preserves normal output while propagating zip errors.
        """
        ApplicationExecutionFilesSolver.output_files = {"bad": object()}

        result = self.app.solve(self.instance_data, self.config)

        self.assertEqual({"assignments": [{"id": 1, "selected": 1}]}, result[0])
        self.assertIsNone(result[4])
        self.assertEqual(EXECUTION_FILES_STATUS_ERROR, result[5])

    def test_check_generate_kpis_propagates_zip_with_solution_data(self):
        """
        Validates that check_generate_kpis propagates zip output with a solution.
        """
        ApplicationExecutionFilesSolver.output_files = {
            "custom/output.txt": io.StringIO("output")
        }

        result = self.app.check_generate_kpis(self.instance_data, self.solution_data)

        self.assertIsNotNone(result[3])
        self.assertEqual(EXECUTION_FILES_STATUS_OK, result[4])
        self.assertIn(
            "custom/output.txt", TestExperimentExecutionFiles._zip_names(result[3])
        )

    def test_check_generate_kpis_propagates_not_generated_without_solution_data(self):
        """
        Validates that check_generate_kpis supports no-solution zip propagation.
        """
        ApplicationExecutionFilesSolver.output_files = None

        result = self.app.check_generate_kpis(self.instance_data)

        self.assertIsNone(result[3])
        self.assertEqual(EXECUTION_FILES_STATUS_NOT_GENERATED, result[4])

    def test_check_generate_kpis_propagates_zip_generation_error(self):
        """
        Validates that check_generate_kpis propagates zip generation errors.
        """
        ApplicationExecutionFilesSolver.output_files = {"bad": object()}

        result = self.app.check_generate_kpis(self.instance_data, self.solution_data)

        self.assertIsNone(result[3])
        self.assertEqual(EXECUTION_FILES_STATUS_ERROR, result[4])


if __name__ == "__main__":
    unittest.main()

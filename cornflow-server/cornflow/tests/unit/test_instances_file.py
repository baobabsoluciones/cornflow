from cornflow.models import InstanceModel
from cornflow.tests.custom_test_case import CustomTestCase
import pulp
from cornflow.tests.const import (
    INSTANCE_FILE_URL,
    INSTANCE_MPS,
    INSTANCE_GC_20,
    INSTANCE_FILE_FAIL,
)


class TestInstances(CustomTestCase):
    def setUp(self):
        super().setUp()
        self.url = INSTANCE_FILE_URL
        self.model = InstanceModel

    def create_new_row_file(self, file, name="test1", description="", filename=None):
        data = dict(name=name, description=description)
        with open(file, "rb") as file_obj:
            if filename is None:
                data["file"] = file_obj
            else:
                data["file"] = (file_obj, filename)
            return self.client.post(
                self.url,
                data=data,
                follow_redirects=True,
                headers={
                    "Content-Type": "multipart/form-data",
                    "Authorization": f"Bearer {self.token}",
                },
            )

    def test_new_instance(self):
        file = INSTANCE_MPS
        response = self.create_new_row_file(file)
        self.assertEqual(201, response.status_code)
        row = self.model.query.get(response.json["id"])
        self.assertEqual(row.id, response.json["id"])
        payload = pulp.LpProblem.fromMPS(file, sense=1)[1].toDict()
        self.assertEqual(row.data, payload)

    def test_new_instance_fail_ext(self):
        file = INSTANCE_MPS
        response = self.create_new_row_file(file, filename="test.json")
        self.assertEqual(400, response.status_code)

    def test_new_instance_fail_ext2(self):
        file = INSTANCE_GC_20
        response = self.create_new_row_file(file)
        self.assertEqual(400, response.status_code)

    def test_new_instance_fail_ext3(self):
        file = INSTANCE_FILE_FAIL
        response = self.create_new_row_file(file, filename="test.mps")
        self.assertEqual(400, response.status_code)

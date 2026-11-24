from cornflow_client import constants as client_constants

from cornflow.shared import const as server_const
from cornflow.shared.const import ALL_DEFAULT_ROLES
from cornflow.tests.const import CONSTANTS_URL
from cornflow.tests.custom_test_case import CustomTestCase


def _int_constants(module, prefix):
    return {
        value
        for name, value in vars(module).items()
        if name.startswith(prefix)
        and isinstance(value, int)
        and not isinstance(value, bool)
    }


class TestConstantsEndpoint(CustomTestCase):
    def get_constants(self, token):
        return self.client.get(
            CONSTANTS_URL,
            follow_redirects=True,
            headers=self.get_header_with_auth(token),
        )

    def test_every_role_can_read_the_constants(self):
        for role in ALL_DEFAULT_ROLES:
            token = self.create_user_with_role(role)
            response = self.get_constants(token)
            self.assertEqual(200, response.status_code, f"role {role}")

    def test_unauthenticated_user_cannot_read_the_constants(self):
        response = self.client.get(CONSTANTS_URL, follow_redirects=True)
        self.assertIn(response.status_code, (400, 401))

    def test_every_constant_is_explained(self):
        # Walks the constants themselves, so a new constant without a
        # message (or a new one missing from the endpoint) fails here.
        expected = {
            "execution_states": _int_constants(server_const, "EXEC_STATE_"),
            "solution_status": _int_constants(client_constants, "SOLUTION_STATUS_"),
            "solver_status": _int_constants(client_constants, "STATUS_"),
            "execution_files_status": _int_constants(
                server_const, "EXECUTION_FILES_STATUS_"
            ),
        }
        response = self.get_constants(self.create_user_with_role(ALL_DEFAULT_ROLES[0]))
        self.assertEqual(200, response.status_code)
        for key, codes in expected.items():
            entries = response.json[key]
            self.assertEqual(codes, {e["code"] for e in entries}, key)
            for entry in entries:
                self.assertTrue(entry["name"], f"{key} {entry['code']}")
                self.assertTrue(entry["message"], f"{key} {entry['code']}")

    def test_messages_match_the_existing_dictionaries(self):
        response = self.get_constants(self.create_user_with_role(ALL_DEFAULT_ROLES[0]))
        states = {e["code"]: e for e in response.json["execution_states"]}
        for code, message in server_const.EXECUTION_STATE_MESSAGE_DICT.items():
            self.assertEqual(message, states[code]["message"])
        self.assertEqual("queued", states[server_const.EXEC_STATE_QUEUED]["name"])
        solver = {e["code"]: e for e in response.json["solver_status"]}
        self.assertEqual(
            client_constants.STATUS_CONV[client_constants.STATUS_OPTIMAL],
            solver[client_constants.STATUS_OPTIMAL]["message"],
        )
        solution = {e["code"]: e for e in response.json["solution_status"]}
        self.assertEqual(
            "feasible", solution[client_constants.SOLUTION_STATUS_FEASIBLE]["name"]
        )

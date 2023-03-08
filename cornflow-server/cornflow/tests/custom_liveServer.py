# Full imports
import cornflow_client as cf
import time
import multiprocessing
import socketserver
import os

# External libraries
from coverage import process_startup, Coverage
from flask import current_app
from flask_testing import LiveServerTestCase

# Internal modules
from cornflow.app import create_app
from cornflow.models import UserRoleModel
from cornflow.commands.access import access_init_command
from cornflow.commands.dag import register_deployed_dags_command_test
from cornflow.commands.permissions import register_dag_permissions_command
from cornflow.shared.const import ADMIN_ROLE, SERVICE_ROLE
from cornflow_core.shared import db
from cornflow.tests.const import PREFIX


class CustomTestCaseLive(LiveServerTestCase):
    def create_app(self):
        app = create_app("testing")
        app.config["LIVESERVER_PORT"] = 5050
        return app

    def set_client(self, server):
        self.client = cf.CornFlow(url=server)
        return self.client

    def login_or_signup(self, user_data):
        try:
            response = self.client.login(user_data["username"], user_data["pwd"])
        except cf.CornFlowApiError:
            response = self.client.sign_up(**user_data)
        return response

    def setUp(self, create_all=True):
        if create_all:
            db.create_all()
        access_init_command(False)
        register_deployed_dags_command_test(verbose=False)
        user_data = dict(
            username="testname",
            email="test@test.com",
            pwd="Testpassword1!",
        )
        self.set_client(self.get_server_url())
        response = self.login_or_signup(user_data)
        self.client.token = response["token"]
        self.url = None
        self.model = None
        self.items_to_check = []
        register_dag_permissions_command(
            open_deployment=current_app.config["OPEN_DEPLOYMENT"], verbose=False
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_user_with_role(self, role_id, data=None):
        if data is None:
            data = {
                "username": "testuser" + str(role_id),
                "email": "testemail" + str(role_id) + "@test.org",
                "password": "Testpassword1!",
            }
        response = self.login_or_signup(data)
        user_role = UserRoleModel({"user_id": response["id"], "role_id": role_id})
        user_role.save()

        db.session.commit()

        return self.login_or_signup(data)["token"]

    def create_service_user(self, data=None):
        return self.create_user_with_role(SERVICE_ROLE, data=data)

    def create_admin(self, data=None):
        return self.create_user_with_role(ADMIN_ROLE, data=data)

    def get_server_url(self):
        """
        Return the url of the test server
        """
        prefix = PREFIX
        if prefix:
            prefix += "/"
        return "http://localhost:%s" % self._port_value.value + prefix

    def _spawn_live_server(self):
        self._process = None
        port_value = self._port_value

        def worker(app, port):
            # Based on solution: http://stackoverflow.com/a/27598916
            # Monkey-patch the server_bind so we can determine the port bound by Flask.
            # This handles the case where the port specified is `0`, which means that
            # the OS chooses the port. This is the only known way (currently) of getting
            # the port out of Flask once we call `run`.

            # process_startup()
            original_socket_bind = socketserver.TCPServer.server_bind
            def socket_bind_wrapper(self):
                ret = original_socket_bind(self)

                # Get the port and save it into the port_value, so the parent process
                # can read it.
                (_, port) = self.socket.getsockname()
                port_value.value = port
                socketserver.TCPServer.server_bind = original_socket_bind
                return ret

            socketserver.TCPServer.server_bind = socket_bind_wrapper
            app.run(port=port, use_reloader=False)

        self._process = CoverageProcess(
            target=worker, args=(self.app, self._configured_port)
        )

        self._process.start()

        # We must wait for the server to start listening, but give up
        # after a specified maximum timeout
        timeout = self.app.config.get('LIVESERVER_TIMEOUT', 5)
        start_time = time.time()

        while True:
            elapsed_time = (time.time() - start_time)
            if elapsed_time > timeout:
                raise RuntimeError(
                    "Failed to start the server after %d seconds. " % timeout
                )

            if self._can_ping_server():
                break


class CoverageProcess(multiprocessing.Process):
    def __init__(self, *args, **kwargs):
        self.config_file = os.getenv("COVERAGE_PROCESS_START", None)
        self.cov_running = False
        self.cov = None
        if self.config_file:
            self.cov = Coverage(config_file=self.config_file, data_suffix=True)
            # self.cov._warn_no_data = False
        super().__init__(*args, **kwargs)

    def run(self):

        if self.config_file:
            print("Running coverage in CoverageProcess")
            self.cov.start()
            self.cov_running = True

            try:
                super().run()
            except Exception:
                self.cov.stop()
                self.cov.save()
                self.cov_running = False

                print("Saving coverage after exception")
                print(os.listdir())
        else:
            super().run()

    def terminate(self) -> None:
        print(os.listdir())
        if self.cov_running:
            self.cov.stop()
            self.cov.save()
            print("Saving in terminate")
            print(os.listdir())
            print(os.listdir("/home/runner/work/cornflow/cornflow/cornflow-server/cornflow/tests/integration/"))
        super().terminate()

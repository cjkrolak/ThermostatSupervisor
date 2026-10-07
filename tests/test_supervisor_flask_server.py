"""Unit tests for supervisor_flask_server.py without network or thermostat access."""

# built-in imports
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

# local imports
from src import supervisor_flask_server as sfs
from src import utilities as util
from tests import unit_test_common as utc


class IntegrationTest(utc.UnitTest):
    """Test registered supervisor routes with mocked subprocess output."""

    def setUp(self) -> None:
        """Use the routed application and isolate mutable supervisor state."""
        super().setUp()
        self.app = sfs.app
        self.enterContext(patch.dict(self.app.config, TESTING=True))
        self.enterContext(patch.object(sfs, "argv", utc.unit_test_argv))
        self.enterContext(patch.object(sfs.sup, "argv", []))
        self.enterContext(patch.object(sfs.api, "uip"))
        # Avoid rate-limit state leaking between repeated route tests.
        self.enterContext(patch.object(sfs.limiter, "enabled", False))
        self.mock_popen = self.enterContext(patch.object(sfs, "Popen"))
        self.mock_popen.return_value.__enter__.return_value.stdout = [
            "supervisor <output>\n"
        ]
        self.client = self.app.test_client()

    def test_supervisor_flask_server(self) -> None:
        """Confirm the browser URL resolves to the registered data endpoint."""
        path = urlsplit(sfs.flask_url).path
        self.assertEqual(path, "/data")
        with self.client.get(path, buffered=True) as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "text/html")
            self.assertIn(
                f"<title>{utc.unit_test_argv[1]} thermostat zone "
                f"{utc.unit_test_argv[2]}, {utc.unit_test_argv[7]} "
                "measurements</title>",
                response.get_data(as_text=True),
            )

    def test_run_supervise_response(self) -> None:
        """Confirm the route passes runtime overrides to the subprocess."""
        with self.client.get("/data", buffered=True) as response:
            self.assertEqual(response.status_code, 200)
        command = self.mock_popen.call_args.args[0]
        self.assertEqual(
            command, ["python", "-u", "-m", "src.supervise"] + utc.unit_test_argv[1:]
        )

    def test_run_supervise_output(self) -> None:
        """Confirm streamed output is rendered and HTML-escaped."""
        with self.client.get("/data", buffered=True) as response:
            content = response.get_data(as_text=True)
            self.assertIn("<code>supervisor &lt;output&gt;</code>", content)
            self.assertIn("<br>\n", content)


if __name__ == "__main__":
    util.log_msg.debug = True  # type: ignore[attr-defined]
    unittest.main(verbosity=2)

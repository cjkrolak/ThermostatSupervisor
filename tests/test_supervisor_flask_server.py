"""
Unit test module for supervise_flask_server.py.

Flask server tests currently do not work on Azure pipelines
because ports cannot be opened on shared pool.
"""
# built-in imports
import threading
import time
import unittest

# third party imports
import requests

# local imports
# thermostat_api is imported but not used to avoid a circular import
from thermostatsupervisor import thermostat_api as api  # noqa F401, pylint: disable=unused-import.
from thermostatsupervisor import supervisor_flask_server as sfs
from tests import unit_test_common as utc
from thermostatsupervisor import utilities as util


@unittest.skipIf(util.is_azure_environment(),
                 "this test not supported on Azure Pipelines")
@unittest.skipIf(not util.is_interactive_environment(),
                 "this test hangs when run from the command line")
@unittest.skipIf(not utc.ENABLE_FLASK_INTEGRATION_TESTS,
                 "flask integration tests are disabled")
class IntegrationTest(utc.UnitTest):
    """Test functions in supervisor_flask_server.py."""

    app = sfs.create_app()

    def setUp(self):
        self.print_test_name()
        sfs.debug = False
        sfs.measurements = 10
        sfs.unit_test_mode = True
        util.log_msg.file_name = "unit_test.txt"
        if not util.is_azure_environment():
            # mock the argv list
            sfs.argv = utc.unit_test_argv
            print(f"DEBUG: in setup supervise sfs.argv={sfs.argv}")
            print("starting supervise flask server thread...")
            self.flask_server = threading.Thread(
                target=sfs.app.run, args=('0.0.0.0', sfs.FLASK_PORT, False),
                kwargs=sfs.flask_kwargs)
            self.flask_server.daemon = True  # make thread daemonic
            self.flask_server.start()
            print(f"thread alive status={self.flask_server.is_alive()}")
            print("Flask server setup is complete")
        else:
            print("WARNING: flask server tests not currently supported on "
                  "Azure pipelines, doing nothing")

    def tearDown(self):
        if not util.is_azure_environment():
            print(f"thread alive status={self.flask_server.is_alive()}")
            if self.flask_server.daemon:
                print("flask server is daemon thread, "
                      "thread will terminate when main thread terminates")
            else:
                print("WARNING: flask server is not daemon thread, "
                      "thread may still be active")
        self.print_test_result()

    def test_supervisor_flask_server(self):
        """
        Confirm Flask server returns valid data.

        This test requires a live thermostat connection to run the
        supervise routine on.
        """
        # grab supervise web page result and display
        flask_url = (sfs.FLASK_URL_PREFIX + util.get_local_ip() + ':' +
                     str(sfs.FLASK_PORT))

        # delay for page load and initial data posting
        wait_delay_sec = 10
        polling_interval_sec = 4
        while wait_delay_sec > 0:
            print("waiting %d seconds for initial supervisor page to "
                  "be populated..." % wait_delay_sec)
            wait_delay_sec -= polling_interval_sec
            time.sleep(polling_interval_sec)  # polling interval

        # grab web page and check response code
        print(f"grabbing web page results from: {flask_url}")
        results = requests.get(flask_url)
        print(f"web page response code={results.status_code}")
        self.assertEqual(results.status_code, 200,
                         f"web page response was {results.status_code}, "
                         f"expected 200")

        # check web page content vs. expectations
        print(f"web page contents: {results.content}")
        exp_substr = \
            ("<title>%s thermostat zone %s, %s measurements</title>" %
             (utc.unit_test_argv[1], utc.unit_test_argv[2],
              utc.unit_test_argv[7]))
        self.assertTrue(exp_substr in results.content.decode("utf-8"),
                        "did not find substring '%s' in web page response")


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
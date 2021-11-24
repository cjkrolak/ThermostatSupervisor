"""
Unit test module for supervise_flask_server.py.

Flask server tests currently do not work on Azure pipelines
because ports cannot be opened on shared pool.
"""
# built-in imports
import requests
import threading
import time
import unittest

# local imports
# thermostat_api is imported but not used to avoid a circular import
import thermostat_api as api  # noqa F401, pylint: disable=unused-import.
import supervisor_flask_server as sfs
import unit_test_common as utc
import utilities as util


class Test(unittest.TestCase):
    """Test functions in supervisor_flask_server.py."""

    app = sfs.create_app()

    def setUp(self):
        sfs.debug = False
        sfs.measurements = 10
        sfs.unit_test_mode = True
        util.log_msg.file_name = "unit_test.txt"
        if not utc.is_azure_environment():
            # mock the argv list
            sfs.argv = utc.unit_test_argv
            print("DEBUG: in setup supervise sfs.argv=%s" % sfs.argv)
            print("starting supervise flask server thread...")
            self.fs = threading.Thread(target=sfs.app.run,
                                       args=('0.0.0.0', sfs.flask_port, False))
            self.fs.daemon = True  # make thread daemonic
            self.fs.start()
            print("thread alive status=%s" % self.fs.is_alive())
            print("Flask server setup is complete")
        else:
            print("WARNING: flask server tests not currently supported on "
                  "Azure pipelines, doing nothing")

    def tearDown(self):
        if not utc.is_azure_environment():
            print("thread alive status=%s" % self.fs.is_alive())
            if self.fs.daemon:
                print("flask server is daemon thread, "
                      "thread will terminate when main thread terminates")
            else:
                print("WARNING: flask server is not daemon thread, "
                      "thread may still be active")

    def test_Supervisor_FlaskServer(self):
        """
        Confirm Flask server returns valid data.

        This test requires a live thermostat connection to run the
        supervise routine on.
        """
        utc.print_test_name()
        if utc.is_azure_environment():
            print("WARNING, TEST ABORT: this test not supported on "
                  "Azure Pipelines, exiting")
            return
        if not util.is_interactive_environment():
            print("WARNING, TEST ABORT: this test hangs when run from "
                  "command line, exiting")
            return

        # grab supervise web page result and display
        flask_url = 'http://' + util.get_local_ip() + ':' + str(sfs.flask_port)

        # delay for page load and initial data posting
        wait_delay_sec = 10
        polling_interval_sec = 4
        while wait_delay_sec > 0:
            print("waiting %d seconds for initial supervisor page to "
                  "be populated..." % wait_delay_sec)
            wait_delay_sec -= polling_interval_sec
            time.sleep(polling_interval_sec)  # polling interval

        # grab web page and check response code
        print("grabbing web page results from: %s" % flask_url)
        results = requests.get(flask_url)
        print("web page response code=%s" % results.status_code)
        self.assertEqual(results.status_code, 200,
                         "web page response was %s, expected 200" %
                         results.status_code)

        # check web page content vs. expectations
        print("web page contents: %s" % results.content)
        exp_substr = \
            ("<title>%s thermostat zone %s, %s measurements</title>" %
             (utc.unit_test_argv[1], utc.unit_test_argv[2],
              utc.unit_test_argv[7]))
        self.assertTrue(exp_substr in results.content.decode("utf-8"),
                        "did not find substring '%s' in web page response")


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()
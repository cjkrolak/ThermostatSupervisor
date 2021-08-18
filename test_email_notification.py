"""
Unit tes module for email_notification.py.
"""
# built-in libraries
import email_notification as eml
import os
import unittest

# local libraries
import unit_test_common as utc
import utilities as util


class Test(unittest.TestCase):

    to_address = None
    from_address = None
    from_password = None

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testCheckEmailEnvVariables(self):
        """
        Verify all required email email env variables are present for tests.

        If this test fails during CI check repository secrets in GitHub.
        If this test fails during manual run check env variables on local PC.
        """
        utc.print_test_name()

        # make sure email account environmental variables are present
        for env_key in ['GMAIL_USERNAME', 'GMAIL_PASSWORD']:
            try:
                print("checking for environment variable key %s" % env_key)
                _ = os.environ[env_key]
                print("environment variable key %s was found (PASS)" % env_key)
            except KeyError:
                fail_msg = ("%s environment variable missing "
                            "from environment" % env_key)
                self.fail(fail_msg)

    def testSendEmailAlerts(self):
        """Test send_email_alerts() functionality."""
        utc.print_test_name()

        # import environment variables for unit testing.
        # These env variables come from repo secrets during CI process
        # or from local machine during manual run.
        # if self.from_address is None:
        #     self.from_address = os.environ['GMAIL_USERNAME']
        # if self.from_password is None:
        #     self.from_password = os.environ['GMAIL_PASSWORD']

        # TODO: GMAIL AUTH IS FAILING, TEST is TEMP DISABLED.
        print("test is temporarily disabled due to gmail auth issue")
        return

        # send message
        body = "this is a test of the email notification alert."
        print("to_address before test: %s" % self.to_address)
        print("from_address before test: %s" % self.from_address)
        print("from_password before test: %s" % self.from_password)
        return_status = \
            eml.send_email_alert(to_address=self.to_address,
                                 from_address=self.from_address,
                                 from_password=self.from_password,
                                 subject="(unittest) test email alert",
                                 body=body)
        self.assertEqual(return_status, util.NO_ERROR)

        body = "this is a test of the email notification alert."
        return_status = \
            eml.send_email_alert(subject="(unittest) test email alert",
                                 body=body)

        self.assertEqual(return_status, util.NO_ERROR)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()

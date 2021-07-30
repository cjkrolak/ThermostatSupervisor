"""
Unit tes module for email_notification.py.
"""
# built-in libraries
import email_notification as eml
import os
import sys
import unittest

# local libraries
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
        # make sure email account environmental variables are present
        for env_key in ['GMAIL_USERNAME', 'GMAIL_PASSWORD',
                        'GMAIL_TO_USERNAME']:
            try:
                print("checking for environment variable key %s" % env_key)
                _ = os.environ[env_key]
            except KeyError:
                fail_msg = ("%s environment variable missing "
                            "from environment" % env_key)
                self.fail(fail_msg)

    def testSendEmailAlerts(self):
        """Test send_email_alerts() functionality."""

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
    # import sys;sys.argv = ['', 'Test.testName']
    if len(sys.argv) > 1 and False:
        Test.to_address = sys.argv.pop()
        Test.from_address = sys.argv.pop()
        Test.from_password = sys.argv.pop()
    util.log_msg.debug = True
    unittest.main()

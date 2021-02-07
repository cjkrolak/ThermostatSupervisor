"""
Unit tes module for email_notification.py.
"""

import email_notification as eml
import sys
import unittest


class Test(unittest.TestCase):

    to_address = None
    from_address = None
    from_password = None

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testName(self):
        body = "this is a test of the email notification alert."
        return_status = \
            eml.send_email_alert(to_address=self.to_address,
                                 from_address=self.from_address,
                                 from_password=self.from_password,
                                 subject="(unittest) test email alert",
                                 body=body,
                                 debug=True)
        self.assertEqual(return_status, eml.NO_ERROR)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    if len(sys.argv) > 1 and False:
        Test.to_address = sys.argv.pop()
        Test.from_address = sys.argv.pop()
        Test.from_password = sys.argv.pop()
    unittest.main()

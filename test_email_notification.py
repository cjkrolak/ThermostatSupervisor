"""
Unit tes module for email_notification.py.
"""

import email_notification as eml
import sys
import unittest


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testName(self):
        if len(sys.argv) >= 3:
            to_address = sys.argv[0]
            from_address = sys.argv[1]
            from_password = sys.argv[2]
        else:
            to_address = None
            from_address = None
            from_password = None
        body = "this is a test of the email notification alert."
        return_status = \
            eml.send_email_alert(to_address=to_address,
                                 from_address=from_address,
                                 from_password=from_password,
                                 subject="(unittest) test email alert",
                                 body=body,
                                 debug=True)
        self.assertEqual(return_status, eml.NO_ERROR)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']

        
    unittest.main()

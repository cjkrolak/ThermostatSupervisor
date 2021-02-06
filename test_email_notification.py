'''
Created on Feb 6, 2021

@author: cjkro
'''
import email_notification as eml
import unittest


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testName(self):
        return_status = \
        eml.send_email_alert(subject="(unittest) test email alert",
                             body="this is a test of the email notification alert.",
                             debug=True)
        self.assertEqual(return_status, eml.NO_ERROR)

        
if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

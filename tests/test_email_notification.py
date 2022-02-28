"""
Unit tes module for email_notification.py.
"""
# built-in libraries
import os
import unittest
from unittest import mock

# local libraries
from thermostatsupervisor import email_notification as eml
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class Test(utc.UnitTest):
    """Test email_notification.py functions."""

    to_address = None
    from_address = None
    from_password = None

    def test_check_email_env_variables(self):
        """
        Verify all required email email env variables are present for tests.

        If this test fails during AzDO CI, check repository secrets stored
        in Azure DevOps variables and also check yml file.
        If this test fails during manual run check env variables in
        local PC environment variables.
        """
        # make sure email account environmental variables are present
        for env_key in ['GMAIL_USERNAME', 'GMAIL_PASSWORD']:
            try:
                print(f"checking for environment variable key {env_key}")
                _ = os.environ[env_key]
                print(f"environment variable key {env_key} was found (PASS)")
            except KeyError:
                fail_msg = (f"{env_key} environment variable missing from "
                            f"environment")
                self.fail(fail_msg)

    def test_send_email_alerts(self):
        """Test send_email_alerts() functionality."""

        # send message with no inputs, UTIL.NO_ERROR expected
        body = "this is a test of the email notification alert."
        return_status, return_status_msg = \
            eml.send_email_alert(subject="test email alert",
                                 body=body)

        fail_msg = (f"send email with defaults failed for status code: "
                    f"{return_status}: {return_status_msg}")
        self.assertEqual(return_status, util.NO_ERROR, fail_msg)

        # send message with bad port, UTIL.CONNECTION_ERROR expected
        body = ("this is a test of the email notification alert with bad "
                "SMTP port input, should fail.")
        return_status, return_status_msg = \
            eml.send_email_alert(server_port=13,
                                 subject="test email alert "
                                 "(bad port)", body=body)
        fail_msg = (f"send email with bad server port failed for status code: "
                    f"{return_status}: {return_status_msg}")
        self.assertEqual(return_status, util.CONNECTION_ERROR, fail_msg)

        # send message with bad email addre, util.AUTHORIZATION_ERROR expected
        body = ("this is a test of the email notification alert with bad "
                "sender email address, should fail.")
        return_status, return_status_msg = \
            eml.send_email_alert(from_address="bogus@gmail.com",
                                 subject="test email alert "
                                 "(bad from address)", body=body)
        fail_msg = (f"send email with bad from addresss failed for status "
                    f"code: {return_status}: {return_status_msg}")
        self.assertEqual(return_status, util.AUTHORIZATION_ERROR, fail_msg)

    @mock.patch.dict(os.environ, {}, clear=True)  # noqa e501, pylint:disable=undefined-variable
    def test_send_email_alert_no_env_key(self):
        """Test send_email_alerts() functionality without email address."""

        # send message with no inputs, UTIL.NO_ERROR expected
        body = "this is a test of the email notification alert."
        return_status, return_status_msg = \
            eml.send_email_alert(subject="test email alert with "
                                 "no email address env key",
                                 body=body)

        fail_msg = (f"send email with no email env key failed for "
                    f"status code: {return_status}: {return_status_msg}")
        self.assertEqual(return_status, util.ENVIRONMENT_ERROR, fail_msg)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)

"""
Unit tes module for email_notification.py.
"""

# built-in libraries
import os
import smtplib
import unittest
from unittest import mock

# local libraries
from src import email_notification as eml
from src import environment as env
from src import utilities as util
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
        for env_key in ["GMAIL_USERNAME", "GMAIL_PASSWORD"]:
            try:
                print(f"checking for environment variable key {env_key}")
                _ = os.environ[env_key]
                print(f"environment variable key {env_key} was found (PASS)")
            except KeyError:
                fail_msg = f"{env_key} environment variable missing from environment"
                self.fail(fail_msg)

    @mock.patch.dict(
        os.environ, {"GMAIL_USERNAME": "test@gmail.com", "GMAIL_PASSWORD": "testpass"}
    )
    def test_send_email_alerts(self):
        """Test send_email_alerts() functionality."""

        # send message with no inputs, UTIL.NO_ERROR expected
        body = "this is a test of the email notification alert."
        return_status, return_status_msg = eml.send_email_alert(
            subject="test email alert (no inputs)", body=body
        )

        fail_msg = (
            f"send email with defaults failed for status code: "
            f"{return_status}: {return_status_msg}"
        )
        self.assertEqual(return_status, util.NO_ERROR, fail_msg)

        # send message with bad port, UTIL.CONNECTION_ERROR expected
        body = (
            "this is a test of the email notification alert with bad "
            "SMTP port input, should fail."
        )
        # Mock SMTP_SSL to raise an OSError for bad port
        with mock.patch("smtplib.SMTP_SSL", side_effect=OSError("Connection refused")):
            # Temporarily disable unit test mode to test connection error
            original_unit_test_mode = util.unit_test_mode
            util.unit_test_mode = False
            try:
                return_status, return_status_msg = eml.send_email_alert(
                    server_port=13, subject="test email alert (bad port)", body=body
                )
            finally:
                util.unit_test_mode = original_unit_test_mode
        fail_msg = (
            f"send email with bad server port failed for status code: "
            f"{return_status}: {return_status_msg}"
        )
        self.assertEqual(return_status, util.CONNECTION_ERROR, fail_msg)

        # send message with bad email address,
        # util.AUTHORIZATION_ERROR expected
        body = (
            "this is a test of the email notification alert with bad "
            "sender email address, should fail."
        )
        # Mock SMTP_SSL and login to raise an SMTPAuthenticationError
        mock_server = mock.Mock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
            535, "Authentication failed"
        )
        with mock.patch("smtplib.SMTP_SSL", return_value=mock_server):
            # Temporarily disable unit test mode to test authorization error
            original_unit_test_mode = util.unit_test_mode
            util.unit_test_mode = False
            try:
                return_status, return_status_msg = eml.send_email_alert(
                    subject="test email alert (bad auth)", body=body
                )
            finally:
                util.unit_test_mode = original_unit_test_mode

        fail_msg = (
            f"send email with bad from address failed for status "
            f"code: {return_status}: {return_status_msg}"
        )
        self.assertEqual(return_status, util.AUTHORIZATION_ERROR, fail_msg)

    def test_send_email_alert_no_env_key(self):
        """Test send_email_alerts() functionality without email address."""

        # cache valid to_address
        to_address_valid = env.get_env_variable("GMAIL_USERNAME")

        # send message with no inputs, UTIL.NO_ERROR expected
        for name_to_omit in ["GMAIL_USERNAME", "GMAIL_PASSWORD"]:
            # to and from address currently share the same env key so add
            # runs with a valid to_address to confirm branch coverage of
            # a missing from address.
            for to_address in [None, to_address_valid]:
                valid_msg = ["valid", "invalid"][bool(to_address is None)]
                print(
                    f"testing send_email_alert() with env key "
                    f"{name_to_omit} missing and {valid_msg} to_address..."
                )
                modified_environ = utc.omit_env_vars(name_to_omit)

                body = (
                    f"this is a test of the email notification alert with "
                    f"env var {name_to_omit} omitted."
                )

                # Temporarily disable unit_test_mode to test environment error
                # conditions
                original_unit_test_mode = util.unit_test_mode
                util.unit_test_mode = False
                try:
                    # Mock both os.environ and supervisor-env.txt file reading
                    # to ensure the test doesn't get credentials from the file
                    with mock.patch.dict(
                        os.environ, modified_environ, clear=True
                    ), mock.patch(
                        "src.environment._read_supervisor_env_file",
                        return_value={}
                    ):
                        return_status, return_status_msg = eml.send_email_alert(
                            to_address=to_address,
                            subject=f"test email alert with "
                            f"env key {name_to_omit} missing",
                            body=body,
                        )

                    fail_msg = (
                        f"send email with no email env key failed for "
                        f"status code: {return_status}: "
                        f"{return_status_msg}"
                    )
                    self.assertEqual(return_status, util.ENVIRONMENT_ERROR, fail_msg)
                finally:
                    # Restore original unit_test_mode
                    util.unit_test_mode = original_unit_test_mode

    @mock.patch.dict(
        os.environ, {"GMAIL_USERNAME": "test@gmail.com", "GMAIL_PASSWORD": "testpass"}
    )
    def test_send_email_alert_smtp_exceptions(self):
        """
        Test send_email_alerts() functionality with mocked exceptions.

        Mail will not be sent due to exception.  Code will continue.
        """
        bogus_exception_code = 99
        bogus_sender = "bogus sender"
        sendmail_exceptions = [
            (smtplib.SMTPHeloError, [bogus_exception_code, "mock SMTPHeloError"]),
            (smtplib.SMTPRecipientsRefused, ["mock SMTPRecipientsRefused"]),
            (
                smtplib.SMTPSenderRefused,
                [bogus_exception_code, "mock SMTPSenderRefused", bogus_sender],
            ),
            (smtplib.SMTPDataError, [bogus_exception_code, "mock SMTPDataError"]),
            (smtplib.SMTPNotSupportedError, ["mock SMTPNotSupportedError"]),
        ]
        for exception, exception_args in sendmail_exceptions:
            print(f"testing mocked '{str(exception)} exception...")

            # mock the exception case
            # Capture loop variables as default args to avoid late binding
            side_effect = (
                lambda *_, exc=exception, args=exception_args, **__: (
                    utc.mock_exception(exc, args)
                )
            )

            # Mock SMTP_SSL and setup to reach the sendmail logic
            mock_server = mock.Mock()
            mock_server.sendmail.side_effect = side_effect

            with mock.patch("smtplib.SMTP_SSL", return_value=mock_server):
                # send message with no inputs, UTIL.NO_ERROR expected
                body = (
                    "this is a test of the email notification alert for exception "
                    f"type {str(exception)}."
                )
                # Temporarily disable unit test mode to test SMTP exceptions
                original_unit_test_mode = util.unit_test_mode
                util.unit_test_mode = False
                try:
                    return_status, return_status_msg = eml.send_email_alert(
                        subject=f"test email alert (mocked {str(exception)} exception)",
                        body=body,
                    )
                finally:
                    util.unit_test_mode = original_unit_test_mode
                fail_msg = (
                    f"send email with mocked SMTP exception returned "
                    f"status code: {return_status}: "
                    f"{return_status_msg}"
                )
                self.assertEqual(return_status, util.EMAIL_SEND_ERROR, fail_msg)


if __name__ == "__main__":
    util.log_msg.debug = True  # type: ignore[attr-defined]
    unittest.main(verbosity=2)

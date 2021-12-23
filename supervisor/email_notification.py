"""
Email notifications from gmail client.

dependencies:
  context variables must be setup:
  'GMAIL_USERNAME':  from address on gmail service
  'GMAIL_PASSWORD':  GMAIL_USERNAME password
"""
# built-in libraries
from email.mime.text import MIMEText
import smtplib
import socket
import sys
import traceback

# local libraries
from supervisor import utilities as util

# tracing data
module_name = sys.modules[__name__]
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
email_trace = ("email sent from module '%s' running on %s (%s)" %
               (module_name, host_name, host_ip))


def send_email_alert(to_address=None,
                     from_address=None,
                     from_password=None,
                     server_url='smtp.gmail.com',
                     server_port=465,
                     subject="", body=""):
    """
    Send an email alert on gmail.

    Email alerts are warnings so all exceptions within this module are caught
    and a status code is returned for the caller to disposition.

    inputs:
        to_address(list): list of email addresses
        from_address(str):  from gmail address
        from_password(str): password for from gmail address
        server_url(str): SMTP server URL
        server_port(int): SMTP server port number
        subject(str):  email subject text
        body(str):     email body text
    returns:
        tuple(status(int), msg(str)):  status or error code, 0 for no error
                                       and descriptive explanation.
    """
    return_status_msg_dict = {
        util.NO_ERROR: "no error",
        util.CONNECTION_ERROR: ("connection error, verify SMTP address "
                                " and port"),
        util.AUTHORIZATION_ERROR: ("authorization error, verify username "
                                   "and password"),
        util.EMAIL_SEND_ERROR: ("email send error, verify SMTP protocol "
                                "is supported by the sending and "
                                "receiving addresses"),
        util.ENVIRONMENT_ERROR: ("failed to retrieve email credentials "
                                 "from context variable"),
        }

    # default email addresses from env variables
    if not to_address:
        buff = util.get_env_variable('GMAIL_USERNAME')
        to_address = buff["value"]
        if buff["status"] != util.NO_ERROR:
            return (buff["status"], return_status_msg_dict[buff["status"]])
    if not from_address:
        buff = util.get_env_variable('GMAIL_USERNAME')
        from_address = buff["value"]
        if buff["status"] != util.NO_ERROR:
            return (buff["status"], return_status_msg_dict[buff["status"]])
    if not from_password:
        buff = util.get_env_variable('GMAIL_PASSWORD')
        from_password = buff["value"]
        if buff["status"] != util.NO_ERROR:
            return (buff["status"], return_status_msg_dict[buff["status"]])

    status = util.NO_ERROR  # default

    # add trace
    body += "\n\n%s" % email_trace

    # build email message
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_address

    util.log_msg("message text=%s" % msg.as_string(),
                 mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)

    try:
        server = smtplib.SMTP_SSL(server_url, server_port)
        util.log_msg("smtp connection successful",
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
    except (ValueError,  # not sure if this exception will be raised here
            TimeoutError,  # observed on Windows for bad port
            OSError  # on AzDO with bad port
            ) as e:
        util.log_msg("exception during smtp connection: %s" % str(e),
                     mode=util.BOTH_LOG, func_name=1)
        return (util.CONNECTION_ERROR, return_status_msg_dict[status])
    server.ehlo()
    try:
        server.login(from_address, from_password)
        util.log_msg("email account authorization "
                     "for account %s successful" % from_address,
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
    except (smtplib.SMTPHeloError, smtplib.SMTPAuthenticationError,
            smtplib.SMTPNotSupportedError, smtplib.SMTPException):
        util.log_msg(traceback.format_exc(),
                     mode=util.BOTH_LOG, func_name=1)
        util.log_msg("exception during email account authorization "
                     "for account %s" % from_address,
                     mode=util.BOTH_LOG, func_name=1)
        server.close()
        return (util.AUTHORIZATION_ERROR, return_status_msg_dict[status])
    try:
        server.sendmail(from_address, to_address, msg.as_string())
        util.log_msg("mail send was successful",
                     mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)
    except (smtplib.SMTPHeloError, smtplib.SMTPRecipientsRefused,
            smtplib.SMTPSenderRefused, smtplib.SMTPDataError,
            smtplib.SMTPNotSupportedError):
        util.log_msg("exception during mail send",
                     mode=util.BOTH_LOG, func_name=1)
        server.close()
        return (util.EMAIL_SEND_ERROR, return_status_msg_dict[status])
    server.close()
    util.log_msg("Email sent!",
                 mode=util.DEBUG_LOG + util.CONSOLE_LOG, func_name=1)

    return (status, return_status_msg_dict[status])


if __name__ == "__main__":
    util.log_msg.debug = True
    send_email_alert(subject="test email alert",
                     body="this is a test of the email notification alert.")
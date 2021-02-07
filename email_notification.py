"""
Email notifications from gmail client.

dependencies:
  environment variables must be setup:
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
import utilities as util

# tracing data
module_name = sys.modules[__name__]
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
email_trace = ("email sent from module '%s' running on %s (%s)" %
               (module_name, host_name, host_ip))


def send_email_alert(to_address=None,
                     from_address=None,
                     from_password=None,
                     subject="", body="", debug=False):
    """
    Send an email alert on gmail.

    inputs:
        to(list):      list of email addresses
        from(str):     from gmail address
        from_password(str): password for from gmail address
        subject(str):  email subject text
        body(str):     email body text
        debug(bool):   True to enable verbose debug loggging
    returns:
        status(int):  status or error code, 0 for no error
    """

    # default email addresses from env variables
    if not to_address:
        buff = util.get_env_variable('GMAIL_USERNAME', debug)
        to_address = buff["value"]
        if buff["status"] != util.NO_ERROR:
            return buff["status"] 
    if not from_address:
        buff = util.get_env_variable('GMAIL_USERNAME', debug)
        from_address = buff["value"]
        if buff["status"] != util.NO_ERROR:
            return buff["status"] 
    if not from_password:
        buff = util.get_env_variable('GMAIL_PASSWORD', debug)
        from_password = buff["value"]
        if buff["status"] != util.NO_ERROR:
            return buff["status"] 

    status = util.NO_ERROR  # default

    # add trace
    body += "\n\n%s" % email_trace

    # build email message
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_address

    util.log_msg("message text=%s" % msg.as_string(),
                 func_name=1, debug=debug)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        util.log_msg("smtp connection successful",
                     func_name=1, debug=debug)
    except ValueError:
        util.log_msg("exception during smtp connection",
                     func_name=1, debug=debug)
        return util.CONNECTION_ERROR
    server.ehlo()
    try:
        server.login(from_address, from_password)
        util.log_msg("email account authorization "
                     "for account %s successful" % from_address,
                     func_name=1, debug=debug)
    except (smtplib.SMTPHeloError, smtplib.SMTPAuthenticationError,
            smtplib.SMTPNotSupportedError, smtplib.SMTPException):
        if debug:
            util.log_msg(traceback.format_exc(),
                     func_name=1, debug=debug)
            util.log_msg("exception during email account authorization "
                         "for account %s" % from_address,
                         func_name=1, debug=debug)
        server.close()
        return util.AUTHORIZATION_ERROR
    try:
        server.sendmail(from_address, to_address, msg.as_string())
        util.log_msg("mail send was successful",
                     func_name=1, debug=debug)
    except (smtplib.SMTPHeloError, smtplib.SMTPRecipientsRefused,
            smtplib.SMTPSenderRefused, smtplib.SMTPDataError,
            smtplib.SMTPNotSupportedError):
        util.log_msg("exception during mail send",
                     func_name=1, debug=debug)
        server.close()
        return util.EMAIL_SEND_ERROR
    server.close()
    util.log_msg("Email sent!",
                 func_name=1, debug=debug)

    return status


if __name__ == "__main__":
    send_email_alert(subject="test email alert",
                     body="this is a test of the email notification alert.",
                     debug=True)

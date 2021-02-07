"""
Email notifications from gmail client.

dependencies:
  environment variables must be setup:
  'GMAIL_USERNAME':  from address on gmail service
  'GMAIL_PASSWORD':  GMAIL_USERNAME password
"""
from email.mime.text import MIMEText
import os
import smtplib
import socket
import sys
import traceback
from pickle import NONE

# status flags
NO_ERROR = 0
CONNECTION_ERROR = 1
AUTHORIZATION_ERROR = 2
EMAIL_SEND_ERROR = 3
ENVIRONMENT_ERROR = 4
OTHER_ERROR = 5

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
        to_address_default = 'GMAIL_USERNAME'
        try:
            to_address = os.environ[to_address_default]
            if debug:
                print("to_address=%s" % to_address)
        except KeyError:
            print("FATAL ERROR: required environment variable '%s'"
                  " is missing." % to_address_default)
            return ENVIRONMENT_ERROR
    if not from_address:
        from_address_default = 'GMAIL_USERNAME'
        try:
            from_address = os.environ[from_address_default]
            if debug:
                print("from_address=%s" % from_address)
        except KeyError:
            print("FATAL ERROR: required environment variable '%s'"
                  " is missing." % from_address_default)
            return ENVIRONMENT_ERROR
    if not from_password:
        from_pwd_default = 'GMAIL_PASSWORD'
        try:
            from_password = os.environ[from_pwd_default]
            if debug:
                print("from_password=%s" % from_password)
        except KeyError:
            print("FATAL ERROR: required environment variable '%s'"
                  " is missing." % from_pwd_default)
            return ENVIRONMENT_ERROR

    status = NO_ERROR

    # add trace
    body += "\n\n%s" % email_trace

    # build email message
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_address

    if debug:
        print("message text=%s" % msg.as_string())

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        if debug:
            print("smtp connection successful")
    except Exception:
        if debug:
            print("exception during smtp connection")
        return CONNECTION_ERROR
    server.ehlo()
    try:
        server.login(from_address, from_password)
        if debug:
            print("email account authorization "
                  "for account %s successful" % from_address)
    except Exception:
        if debug:
            print(traceback.format_exc())
            print("exception during email account authorization "
                  "for account %s" % from_address)
        server.close()
        return AUTHORIZATION_ERROR
    try:
        server.sendmail(from_address, to_address, msg.as_string())
        if debug:
            print("mail send was successful")
    except Exception:
        if debug:
            print("exception during mail send")
        server.close()
        return EMAIL_SEND_ERROR
    server.close()
    if debug:
        print("Email sent!")

    return status

def get_env_variable(env_key, debug=False):
    """
    Get env variable.
    
    inputs:
       env_key(str): env variable of interest
       debug(bool): verbose debugging
    returns:
       (tuple): (status, value)
    """
    # defaults
    status = NO_ERROR
    env_value = None

    try:
        env_value = os.environ[env_key]
        if debug:
            print("%s=%s" % (env_key, env_value))
    except KeyError:
        print("FATAL ERROR: required environment variable '%s'"
              " is missing." % env_key)
        status = ENVIRONMENT_ERROR
    return (status, env_value)
    

if __name__ == "__main__":
    send_email_alert(subject="test email alert",
                     body="this is a test of the email notification alert.",
                     debug=True)

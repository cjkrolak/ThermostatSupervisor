"""
Email notifications from gmail client
"""
import os
import smtplib

# status flags
NO_ERROR = 0
CONNECTION_ERROR = 1
AUTHORIZATION_ERROR = 2
EMAIL_SEND_ERROR = 3
OTHER_ERROR = 4


def send_email_alert(to_address_lst=[os.environ['GMAIL_TO_USERNAME']], from_address=os.environ['GMAIL_USERNAME'],
                     from_password=os.environ['GMAIL_PASSWORD'], subject="", body="", debug=False):
    """
    Send an email alert on gmail.
    
    inputs:
        to(list):      list of email addresses
        from(str):     from gmail address
        from_pwd(str): password for from gmail address
        subject(str):  email subject text
        body(str):     email body text
        debug(bool):   True to enable verbose debug loggging
    returns:
        status(int):  status or error code, 0 for no error
    """
    status = NO_ERROR

    email_text = """\
    From: %s
    To: %s
    Subject: %s
    
    %s
    """ % (from_address, ", ".join(to_address_lst), subject, body)
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    except:
        if debug:
            print("exception during smtp connection")
        return CONNECTION_ERROR
    server.ehlo()
    try:
        server.login(from_address, from_password)
    except:
        if debug:
            print("exception during email account authorization")
        server.close()
        return AUTHORIZATION_ERROR
    try:
        server.sendmail(from_address, to_address_lst, email_text)
    except:
        if debug:
            print("exception during mail send")
        server.close()
        return EMAIL_SEND_ERROR
    server.close()
    if debug:
        print("Email sent!")

    return status
import smtplib
import threading
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import time

load_dotenv()

def _send_email_core(to_email, subject, body, html_body=None):
    start = time.time()

    smtp_host = os.getenv('MAIL_SERVER', 'smtp.hostinger.com')
    smtp_port = int(os.getenv('MAIL_PORT', 465))
    smtp_user = os.getenv('MAIL_USERNAME')
    smtp_pass = os.getenv('MAIL_PASSWORD')
    from_email = os.getenv('MAIL_DEFAULT_SENDER')

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.set_content(body)

        if html_body:
            msg.add_alternative(html_body, subtype='html')

        if smtp_port == 587:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(smtp_user, smtp_pass)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as smtp:
                smtp.login(smtp_user, smtp_pass)
                smtp.send_message(msg)

        elapsed = time.time() - start
        print(f"✅ EMAIL SENT to {to_email} in {elapsed:.2f} seconds")
        return True

    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ EMAIL ERROR ({to_email}) after {elapsed:.2f} seconds: {str(e)}")
        return False


def send_email(to_email, subject, body, html_body=None, use_background=True):
    """
    Sends an email using Hostinger SMTP.
    Default is use_background=True to prevent blocking the main request thread.
    """
    if use_background:
        thread = threading.Thread(
            target=_send_email_core,
            args=(to_email, subject, body, html_body),
            daemon=True
        )
        thread.start()
        return True

    return _send_email_core(to_email, subject, body, html_body)
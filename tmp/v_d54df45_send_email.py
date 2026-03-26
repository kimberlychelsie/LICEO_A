import smtplib
from email.message import EmailMessage
import os
import threading
import logging

logger = logging.getLogger(__name__)

def _send_email_async(to_email, subject, body):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        logger.error(
            "EMAIL SEND FAILED: SMTP_USER or SMTP_PASS environment variable is not set! "
            f"SMTP_USER={'SET' if smtp_user else 'MISSING'}, "
            f"SMTP_PASS={'SET' if smtp_pass else 'MISSING'}"
        )
        return

    msg = EmailMessage()
    msg["From"] = f"Liceo LMS <{smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"EMAIL SEND FAILED to {to_email}: {type(e).__name__}: {e}")

def send_email(to_email, subject, body):
    """
    Sends an email asynchronously using a background thread so it doesn't 
    block web requests and cause Gunicorn timeouts on Railway.
    """
    thread = threading.Thread(target=_send_email_async, args=(to_email, subject, body))
    thread.daemon = True
    thread.start()
    return True
import smtplib
from email.message import EmailMessage
import os
import threading

def _send_email_async(to_email, subject, body):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    msg = EmailMessage()
    msg["From"] = f"Liceo LMS <{smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        # Added a 10-second timeout to prevent stalling even in the background thread
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email async to {to_email}: {e}")

def send_email(to_email, subject, body):
    """
    Sends an email asynchronously using a background thread so it doesn't 
    block web requests and cause Gunicorn timeouts on Railway.
    """
    thread = threading.Thread(target=_send_email_async, args=(to_email, subject, body))
    thread.daemon = True
    thread.start()
    return True
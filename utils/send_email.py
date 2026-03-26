import smtplib
from email.message import EmailMessage
import os
import threading
import socket
import ssl

def _send_email_async(to_email, subject, body):
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        return

    msg = EmailMessage()
    msg["From"] = f"Liceo LMS <{smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # Try 465 (SSL) then 587 (STARTTLS)
    # Using multiple hosts and ports for robustness on Railway
    configs = [
        ("smtp.gmail.com", 465, True),
        ("smtp.googlemail.com", 465, True),
        ("smtp.gmail.com", 587, False),
        ("smtp.googlemail.com", 587, False),
    ]

    for host, port, use_ssl in configs:
        try:
            if use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(host, port, timeout=30, context=context) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=30) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            
            # If successful, stop trying other configs
            return
        except Exception as e:
            print(f"SMTP attempt failed on {host}:{port}: {e}")
            continue

def send_email(to_email, subject, body):
    """
    Sends an email asynchronously using a background thread.
    Includes IPv4 forcing and port 465/587 fallbacks.
    """
    thread = threading.Thread(target=_send_email_async, args=(to_email, subject, body))
    thread.daemon = True
    thread.start()
    return True
import smtplib
from email.message import EmailMessage
import os
import ssl
import traceback

def send_email(to_email, subject, body):
    """
    Sends email (synchronously for reliability in Railway).
    """

    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        print("[EMAIL] ERROR: Missing SMTP_USER or SMTP_PASS environment variables")
        return False

    msg = EmailMessage()
    msg["From"] = f"Liceo LMS <{smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    configs = [
        ("smtp.gmail.com", 465, True),
        ("smtp.gmail.com", 587, False),
    ]

    for host, port, use_ssl in configs:
        try:
            print(f"[EMAIL] Trying {host}:{port} (SSL={use_ssl})")

            if use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=20) as server:
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)

            print(f"[EMAIL] SUCCESS → Sent to {to_email}")
            return True

        except Exception as e:
            print(f"[EMAIL] FAILED on {host}:{port}")
            print(traceback.format_exc())

    print(f"[EMAIL] CRITICAL: All SMTP attempts failed for {to_email}")
    return False
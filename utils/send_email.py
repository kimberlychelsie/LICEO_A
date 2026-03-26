import smtplib
from email.message import EmailMessage
import os
import threading
import ssl

def _send_email_async(to_email, subject, body):
    # Retrieve from env vars or use the explicitly provided credentials
    smtp_user = os.environ.get("SMTP_USER", "biticonmr@gmail.com")
    smtp_pass = os.environ.get("SMTP_PASS", "bjhfwlshpxkcveln")

    if not smtp_user or not smtp_pass:
        print("[EMAIL] Error: SMTP credentials are not configured!")
        return

    msg = EmailMessage()
    msg["From"] = f"Liceo LMS <{smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # Some PaaS like Railway have issues with IPv6 for SMTP. We try SSL on 465 first, then STARTTLS on 587
    configs = [
        ("smtp.gmail.com", 465, True),   # Implicit SSL
        ("smtp.gmail.com", 587, False),  # Explicit TLS
    ]

    for host, port, use_ssl in configs:
        try:
            print(f"[EMAIL] Attempting to send via {host}:{port} (SSL: {use_ssl})...")
            
            if use_ssl:
                # Use a default context for secure SSL connection
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=15) as server:
                    # Identify ourselves, prompt server for supported features
                    server.ehlo()
                    # Start TLS for security
                    server.starttls(context=ssl.create_default_context())
                    # Re-identify ourselves over TLS connection
                    server.ehlo()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            
            print(f"[EMAIL] Successfully sent to {to_email} via {host}:{port}")
            return  # Success, exit the loop
            
        except Exception as e:
            print(f"[EMAIL] Failed attempt on {host}:{port}: {str(e)}")
            continue

    print(f"[EMAIL] Critical Error: All SMTP attempts failed for {to_email}!")

def send_email(to_email, subject, body):
    """
    Sends an email asynchronously using a background thread to prevent UI blocking or WORKER TIMEOUTs.
    """
    print(f"[EMAIL] Queuing email to {to_email}...")
    thread = threading.Thread(target=_send_email_async, args=(to_email, subject, body))
    thread.daemon = True
    thread.start()
    return True
import smtplib
import ssl
import socket
import threading
from email.message import EmailMessage
import os
import logging

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def _send_email_sync(to_email, subject, body):
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        print(f"❌ [EMAIL] SMTP_USER or SMTP_PASS is MISSING! User: {smtp_user}")
        return False

    print(f"📧 [EMAIL] Attempting to send to {to_email} (IPv4 Forced)...")

    msg = EmailMessage()
    msg["From"] = f"Liceo LMS <{smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # List of (host, port, use_ssl) to try
    # Prioritize 587 (STARTTLS) and try googlemail.com which is sometimes less restricted
    configs = [
        ("smtp.googlemail.com", 587, False), # STARTTLS
        ("smtp.gmail.com", 587, False),      # STARTTLS (alt)
        ("smtp.googlemail.com", 465, True),  # SSL
        ("smtp.gmail.com", 465, True),       # SSL (alt)
    ]

    last_error = None
    for host, port, use_ssl in configs:
        try:
            print(f"🔗 [EMAIL] Trying {host}:{port} ({'SSL' if use_ssl else 'STARTTLS'})...")
            
            # Force IPv4 resolution to avoid "Network is unreachable" issues on Railway
            try:
                addr_info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
                target_ip = addr_info[0][4][0]
                print(f"📍 [EMAIL] Resolved {host} to IPv4: {target_ip}")
            except Exception as ree:
                print(f"⚠️ [EMAIL] DNS Resolve failed: {ree}. Using hostname instead.")
                target_ip = host

            if use_ssl:
                context = ssl.create_default_context()
                # Increase timeout to 30s
                with smtplib.SMTP_SSL(target_ip, port, timeout=30, context=context) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                # Increase timeout to 30s
                with smtplib.SMTP(target_ip, port, timeout=30) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            
            print(f"✅ [EMAIL] Sent successfully to {to_email} via {host}:{port}")
            return True
        except Exception as e:
            last_error = e
            print(f"⚠️ [EMAIL] Failed on port {port}: {e}")
            continue

    print(f"❌ [EMAIL] ALL ATTEMPTS FAILED to {to_email}: {last_error}")
    logger.error(f"EMAIL SEND FAILED to {to_email}: {last_error}")
    return False

def send_email(to_email, subject, body):
    # Re-enable ASYNCHRONOUS so it doesn't block and crash Gunicorn on Railway
    thread = threading.Thread(target=_send_email_sync, args=(to_email, subject, body))
    thread.daemon = True
    thread.start()
    return True
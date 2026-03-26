import os
import logging
import threading
import json
import urllib.request
import smtplib
import ssl
import socket
from email.message import EmailMessage

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def _send_email_resend(api_key, to_email, subject, body):
    """Sends email using Resend API (HTTPS) - Fallback"""
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {"from": "Liceo LMS <onboarding@resend.dev>", "to": [to_email], "subject": subject, "text": body}
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            return True
    except Exception as e:
        print(f"❌ [RESEND] FAILED: {e}")
        return False

def _send_email_smtp_sync(to_email, subject, body):
    """Primary SMTP logic with IPv4 Forcing and Fallback Ports"""
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        print(f"❌ [SMTP] MISSING credentials for {to_email}")
        return False

    print(f"📧 [SMTP] Attempting to send to {to_email} (IPv4 Forced)...")

    msg = EmailMessage()
    msg["From"] = f"Liceo LMS <{smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # Try 465 (SSL) then 587 (STARTTLS)
    configs = [
        ("smtp.gmail.com", 465, True),
        ("smtp.googlemail.com", 465, True),
        ("smtp.gmail.com", 587, False),
        ("smtp.googlemail.com", 587, False),
    ]

    for host, port, use_ssl in configs:
        try:
            print(f"🔗 [SMTP] Trying {host}:{port} ({'SSL' if use_ssl else 'STARTTLS'})...")
            # Force IPv4
            addr_info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
            target_ip = addr_info[0][4][0]

            if use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(target_ip, port, timeout=20, context=context) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(target_ip, port, timeout=20) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            
            print(f"✅ [SMTP] Sent successfully!")
            return True
        except Exception as e:
            print(f"⚠️ [SMTP] Failed on {port}: {e}")
            continue
    return False

def _combined_send(to_email, subject, body):
    # Try SMTP first (User requested)
    if _send_email_smtp_sync(to_email, subject, body):
        return True
    
    # Try Resend as fallback if key exists
    resend_key = os.environ.get("RESEND_API_KEY")
    if resend_key:
        print("🔄 [SMTP FAILED] Trying Resend fallback...")
        if _send_email_resend(resend_key, to_email, subject, body):
            print("✅ [RESEND] Fallback worked!")
            return True
    return False

def send_email(to_email, subject, body):
    # Always async to avoid timeouts
    thread = threading.Thread(target=_combined_send, args=(to_email, subject, body))
    thread.daemon = True
    thread.start()
    return True
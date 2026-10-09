import smtplib
import threading
from email.message import EmailMessage
import os
import time
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()

def _mask_email(email):
    email = (email or "").strip()
    if "@" not in email:
        return "[missing]"
    name, domain = email.split("@", 1)
    if not name:
        masked_name = "*"
    elif len(name) == 1:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "***" + name[-1]
    return f"{masked_name}@{domain}"

def _sanitize_email_error(err):
    err_name = err.__class__.__name__
    smtp_code = getattr(err, "smtp_code", None)
    if smtp_code:
        return f"{err_name} code={smtp_code}"
    return err_name

def _send_email_core(to_email, subject, body, html_body=None):
    load_dotenv()
    start = time.time()
    safe_to = _mask_email(to_email)

    smtp_user = (os.getenv('MAIL_USERNAME') or os.getenv('SMTP_USER') or os.getenv('MAIL_USER') or '').strip()
    smtp_pass = (os.getenv('MAIL_PASSWORD') or os.getenv('SMTP_PASS') or '').strip().replace(' ', '')

    
    # Auto-detect host & port if not explicitly set
    smtp_host = os.getenv('MAIL_SERVER') or os.getenv('SMTP_HOST')
    if not smtp_host:
        if smtp_user and 'gmail.com' in smtp_user.lower():
            smtp_host = 'smtp.gmail.com'
        else:
            smtp_host = 'smtp.hostinger.com'

    port_env = os.getenv('MAIL_PORT') or os.getenv('SMTP_PORT')
    if port_env:
        smtp_port = int(port_env)
    else:
        smtp_port = 465 if 'gmail.com' in (smtp_host or '').lower() else 465

    from_email = os.getenv('MAIL_DEFAULT_SENDER') or smtp_user or 'noreply@liceo-lms.com'

    if not smtp_user or not smtp_pass:
        print(f"[EMAIL WARNING] Credentials missing (SMTP_USER/MAIL_USERNAME). Email to {safe_to} skipped.")
        return False

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.set_content(body)

        if html_body:
            msg.add_alternative(html_body, subtype='html')

        sent_ok = False
        # Try primary port (SSL 465 or TLS 587)
        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, 465, timeout=12) as smtp:
                    smtp.login(smtp_user, smtp_pass)
                    smtp.send_message(msg)
                    sent_ok = True
            else:
                with smtplib.SMTP(smtp_host, 587, timeout=12) as smtp:
                    smtp.starttls()
                    smtp.login(smtp_user, smtp_pass)
                    smtp.send_message(msg)
                    sent_ok = True
        except Exception as first_err:
            # Fallback to alternative port if primary fails
            alt_port = 587 if smtp_port == 465 else 465
            if alt_port == 465:
                with smtplib.SMTP_SSL(smtp_host, 465, timeout=12) as smtp:
                    smtp.login(smtp_user, smtp_pass)
                    smtp.send_message(msg)
                    sent_ok = True
            else:
                with smtplib.SMTP(smtp_host, 587, timeout=12) as smtp:
                    smtp.starttls()
                    smtp.login(smtp_user, smtp_pass)
                    smtp.send_message(msg)
                    sent_ok = True

        elapsed = time.time() - start
        print(f"[EMAIL SUCCESS] SMTP accepted message to {safe_to} in {elapsed:.2f}s")
        return True

    except Exception as e:
        elapsed = time.time() - start
        print(f"[EMAIL ERROR] SMTP handoff failed for {safe_to} after {elapsed:.2f}s: {_sanitize_email_error(e)}")
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

import smtplib
import threading
from email.message import EmailMessage

def _send_email_core(to_email, subject, body, html_body=None):
    """Internal function to handle the actual SMTP connection."""
    gmail_user = "biticonmr@gmail.com"
    gmail_pass = "ohny yttw tgwq dayg"  
    from_email = "LiceoLMS <biticonmr@gmail.com>"  

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.set_content(body)

        if html_body:
            msg.add_alternative(html_body, subtype='html')

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.send_message(msg)

        print(f"🔥 EMAIL STATUS: SENT to {to_email}")
        return True

    except Exception as e:
        print(f"🔥 EMAIL ERROR ({to_email}):", str(e))
        return False

def send_email(to_email, subject, body, html_body=None, use_background=True):
    """
    Sends an email using Gmail SMTP.
    Default is use_background=True to prevent blocking the main request thread.
    """
    if use_background:
        thread = threading.Thread(target=_send_email_core, args=(to_email, subject, body, html_body))
        thread.start()
        return True
    else:
        return _send_email_core(to_email, subject, body, html_body)
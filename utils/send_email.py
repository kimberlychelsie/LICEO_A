import smtplib
from email.message import EmailMessage

def send_email(to_email, subject, body):
    gmail_user = "biticonmr@gmail.com"
    gmail_pass = "ohny yttw tgwq dayg"  

    from_email = "LiceoLMS <biticonmr@gmail.com>"  

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.send_message(msg)

        print("🔥 EMAIL STATUS: SENT (SMTP)")
        return True

    except Exception as e:
        print("🔥 EMAIL ERROR:", str(e))
        return False
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv
load_dotenv()

def test_send():
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    
    if not smtp_user or not smtp_pass:
        print("Error: SMTP_USER or SMTP_PASS missing")
        return

    msg = EmailMessage()
    msg["From"] = f"Liceo LMS <{smtp_user}>"
    msg["To"] = smtp_user # Send to self
    msg["Subject"] = "Test Email"
    msg.set_content("This is a test email.")

    print(f"Connecting to smtp.gmail.com:465 as {smtp_user}...")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            print("Login in...")
            server.login(smtp_user, smtp_pass)
            print("Sending...")
            server.send_message(msg)
        print("Success!")
    except Exception as e:
        print(f"Failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_send()

import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

def test_smtp():
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    
    print(f"Testing with: {smtp_user}")
    
    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = smtp_user # Send to self
    msg["Subject"] = "SMTP Test"
    msg.set_content("This is a test.")
    
    try:
        print("Trying Port 465 (SSL)...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print("SUCCESS on 465!")
        return
    except Exception as e:
        print(f"FAILED on 465: {e}")
        
    try:
        print("Trying Port 587 (STARTTLS)...")
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print("SUCCESS on 587!")
    except Exception as e:
        print(f"FAILED on 587: {e}")

if __name__ == "__main__":
    test_smtp()

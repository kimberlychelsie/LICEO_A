import requests
import os

def send_email(to_email, subject, body):
    api_key = os.environ.get("RESEND_API_KEY")

    if not api_key:
        print("[EMAIL] ERROR: Missing RESEND_API_KEY")
        return False

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": "Liceo LMS <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "text": body
            },
            timeout=10
        )

        print("🔥 EMAIL STATUS:", response.status_code)
        print("🔥 EMAIL RESPONSE:", response.text)

        return response.ok

    except Exception as e:
        print("🔥 EMAIL ERROR:", str(e))
        return False
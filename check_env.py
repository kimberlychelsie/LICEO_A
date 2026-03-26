import os
from dotenv import load_dotenv
load_dotenv()

print(f"SMTP_USER: {os.getenv('SMTP_USER')}")
print(f"SMTP_PASS: {'SET' if os.getenv('SMTP_PASS') else 'MISSING'}")
print(f"FLASK_APP: {os.getenv('FLASK_APP')}")

import psycopg2
import sys
from werkzeug.security import generate_password_hash

URL = sys.argv[1] if len(sys.argv) > 1 else input("Railway URL: ").strip()
NEW_PASS = sys.argv[2] if len(sys.argv) > 2 else input("New password for liceo_de_majayjay_admin: ").strip()

conn = psycopg2.connect(URL, sslmode="require")
cur = conn.cursor()
cur.execute(
    "UPDATE users SET password=%s WHERE username='liceo_de_majayjay_admin'",
    (generate_password_hash(NEW_PASS),)
)
conn.commit()
print(f"Password updated for liceo_de_majayjay_admin -> {NEW_PASS}")
cur.close(); conn.close()

from dotenv import load_dotenv
load_dotenv()
from db import get_db_connection

db = get_db_connection()
c = db.cursor()

c.execute("SELECT term_name, COUNT(*) FROM section_teachers GROUP BY term_name")
print('section_teachers term_name counts:', c.fetchall())

c.execute("SELECT term_name, COUNT(*) FROM schedules GROUP BY term_name")
print('schedules term_name counts:', c.fetchall())

c.close()
db.close()

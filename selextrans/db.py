import sqlite3
from selextrans.paths import AbsolutePath

# init db
conn = sqlite3.connect(AbsolutePath("data/selextrans.db"))
cursor = conn.cursor()
cursor.close()
conn.close()

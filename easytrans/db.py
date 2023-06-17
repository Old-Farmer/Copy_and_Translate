import sqlite3
from easytrans.paths import AbsolutePath

# init db
conn = sqlite3.connect(AbsolutePath('data/easytrans.db'))
cursor = conn.cursor()
cursor.close()
conn.close()
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('helios.db')
c = conn.cursor()
c.execute('SELECT id, role, content FROM chat_messages ORDER BY id DESC LIMIT 15')
rows = c.fetchall()
for r in reversed(rows):
    line = r[2].replace('\n', ' ')[:140]
    print(f"[{r[0]}] {r[1]}: {line}")

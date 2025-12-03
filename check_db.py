import sqlite3
import os
db_path = os.path.join('backend', 'database', 'history.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:', tables)
for table_name in [t[0] for t in tables]:
    cur.execute(f'PRAGMA table_info({table_name})')
    cols = cur.fetchall()
    print(f'{table_name}: {cols}')
    cur.execute(f'SELECT COUNT(*) FROM {table_name}')
    count = cur.fetchone()[0]
    print(f'  Row count: {count}')
conn.close()

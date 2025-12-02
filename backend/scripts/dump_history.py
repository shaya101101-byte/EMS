import sqlite3, os

db = os.path.join(os.path.dirname(__file__), '..', 'database', 'history.db')
print('DB path:', db)
if not os.path.exists(db):
    print('history.db not found')
    exit(0)
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()
print('Tables:', tables)
for tbl in tables:
    t = tbl[0]
    try:
        cur.execute(f'SELECT rowid, * FROM {t} ORDER BY rowid DESC LIMIT 10')
        rows = cur.fetchall()
        print('\nTable', t, 'latest rows:')
        for r in rows:
            print(r)
    except Exception as e:
        print('Could not read table', t, 'error', e)
conn.close()

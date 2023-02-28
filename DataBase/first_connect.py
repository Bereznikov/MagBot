import psycopg2
from db_password import password

conn = psycopg2.connect(f"dbname='zamhrork' user='zamhrork' host='mouse.db.elephantsql.com' password={password}")
print(conn)
cur = conn.cursor()
insert_query = """ INSERT INTO shop VALUES (%s,%s)"""
for i in range(3, 1000):
    cur.execute(insert_query, (i, 'a' * (i % 10)))
conn.commit()
cur.close()
conn.close()
print(i)
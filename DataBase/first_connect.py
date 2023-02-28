import psycopg2

conn = psycopg2.connect(dbname='northwind', user='avjustice')
print(conn)
cur = conn.cursor()

cur.execute("SELECT * FROM orders LIMIT 10")
records = cur.fetchall()
print(records)
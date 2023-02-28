import psycopg2
from db_password import password_railway

conn = psycopg2.connect(f"dbname='railway' user='postgres' "
                        f"port=5522 host='containers-us-west-91.railway.app' password={password_railway}")
print(conn)
cur = conn.cursor()
insert_query = """ INSERT INTO shop VALUES (%s,%s)"""
select_query = """SELECT * FROM shop WHERE shop_id % 13 = 0"""
cur.execute(select_query)
records = cur.fetchall()
print(records)
# for i in range(1000, 1100):
#     cur.execute(insert_query, (i, 'a' * (i % 10)))
# conn.commit()
# print(i)
cur.close()
conn.close()
# print(i)
import psycopg2
import os

HOST = os.getenv('HOST')
RAILWAY_PASSWORD = os.getenv('RAILWAY_PASSWORD')

class PostgresConnection:
    def __init__(self):
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=HOST,
                                      password=RAILWAY_PASSWORD)
        connection.autocommit = True
        self.connection = connection

    def strong_check(self):
        try:
            cur = self.connection.cursor()
            cur.execute('SELECT 1')
            cur.close()
            return False
        except psycopg2.OperationalError as ex:
            self.update()
            return True

    def simple_check(self):
        if self.connection.closed != 0:
            self.update()

    def update(self):
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=HOST,
                                      password=RAILWAY_PASSWORD)
        connection.autocommit = True
        self.connection = connection

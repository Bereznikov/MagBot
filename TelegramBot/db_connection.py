import psycopg2
from db_password import host, password_railway


class PostgresConnection:
    def __init__(self):
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                                      password=password_railway)
        connection.autocommit = True
        self.connection = connection

    def check_connection(self):
        try:
            cur = self.connection.cursor()
            cur.execute('SELECT 1')
        except Exception as ex:
            print(ex)
            self.update()

    def update(self):
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                                      password=password_railway)
        connection.autocommit = True
        self.connection = connection

import psycopg2
import os
# from db_password import host as HOST, password_railway as PASSWORD_RAILWAY


class PostgresConnection:
    def __init__(self):
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=os.getenv('HOST'),
                                      password=os.getenv('PASSWORD_RAILWAY'))
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
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=os.getenv('HOST'),
                                      password=os.getenv('PASSWORD_RAILWAY'))
        connection.autocommit = True
        self.connection = connection

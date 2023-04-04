import psycopg2
from db_password import host, password_railway


class PostgresConnection:
    def __init__(self):
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                                      password=password_railway)
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
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                                      password=password_railway)
        connection.autocommit = True
        self.connection = connection

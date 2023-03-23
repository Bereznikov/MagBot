import psycopg2
from db_password import host, password_railway
# from psycopg2 import pool


class PostgresConnection:
    def __init__(self):
        # postgres_pool = psycopg2.pool.SimpleConnectionPool(2, 5, dbname='railway', user='postgres', port=5522,
        #                                                    host=host,
        #                                                    password=password_railway)
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                                      password=password_railway)
        connection.autocommit = True
        self.connection = connection
        # self.pool = postgres_pool

    def strong_check(self):
        try:
            cur = self.connection.cursor()
            cur.execute('SELECT 1')
            cur.close()
        except Exception as ex:
            print(ex.__class__, 'Connection was lost and updated')
            self.update()

    def status_check(self):
        try:
            self.connection.isolation_level
        except Exception as ex:
            print(ex)
            self.update()

    def medium_check(self):
        try:
            cur = self.connection.cursor()
            # cur.execute('SELECT shipper_id FROM shipper')
        except Exception as ex:
            print(ex)
            self.update()

    def simple_check(self):
        if self.connection.closed != 0:
            self.update()

    def update(self):
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                                      password=password_railway)
        connection.autocommit = True
        self.connection = connection

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import select
from db_password import password_railway, host
import asyncio
import json

from telegram import *
from key import key_admin as key


async def send_to_admin(username, order_id, order_time, bot):
    text = f'Покупатель с ником: @{username}\nCделал заказ № {order_id}\n' \
           f'{order_time}\n' \
           f'Полная информация в Базе данных.'
    await bot.send_message(text=text, chat_id=106683136)


async def main():
    bot = Bot(key)
    conn = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                            password=password_railway)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute(f"LISTEN orders;")

    while True:
        if select.select([conn], [], [], 5) == ([], [], []):
            print("Timeout")
        else:
            conn.poll()
        # check_query = """SELECT customer_id FROM customer"""
        # cursor.execute(check_query)
        # print(cursor.fetchone()[0])
        for notify in conn.notifies:
            order = json.loads(notify.payload)
            customer_id = order["customer_id"]
            order_id = order["order_id"]
            order_time = order['order_time']
            order_time = f'Дата: {order_time[:10]} Время: {order_time[11:19]}'
            select_query = \
                """SELECT username
                FROM customer
                WHERE customer_id = %s"""
            cursor.execute(select_query, (customer_id,))
            username = cursor.fetchone()[0]
            print(f'Пришел заказ {order_id} от {customer_id}')
            await send_to_admin(username, order_id, order_time, bot)

        conn.notifies.clear()


if __name__ == '__main__':
    asyncio.run(main())
#
# loop = asyncio.get_event_loop()
# loop.add_reader(conn, handle_notify)
# loop.add_reader(echo)
# loop.run_forever()

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import select
from db_password import password_railway, host
import asyncio
import json

from telegram import *
from key import key_admin as key
from telegram.ext import *


async def main():
    bot = Bot(key)

    async def send_to_admin(customer_id, order_id, order_time):
        text = f'Покупатель с tg_id: {customer_id}\nсделал заказg под номером {order_id}\nв {order_time}\n' \
               f'Полная информация в Базе данных.'

        await bot.send_message(text=text, chat_id=106683136)
        # await bot.send_message(text=text, chat_id=186027538)

    conn = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                            password=password_railway)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute(f"LISTEN orders;")
    # cursor.execute(f"LISTEN order_detail;")

    while True:
        conn.poll()
        for notify in conn.notifies:
            if notify[1] == 'orders':
                order = json.loads(notify.payload)
                customer_id = order["customer_id"]
                order_id = order["order_id"]
                order_time = order['order_time']
                await send_to_admin(customer_id, order_id, order_time)
                print(notify.payload)

        conn.notifies.clear()


if __name__ == '__main__':
    asyncio.run(main())
#
# loop = asyncio.get_event_loop()
# loop.add_reader(conn, handle_notify)
# loop.add_reader(echo)
# loop.run_forever()

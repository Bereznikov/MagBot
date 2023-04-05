import os

import asyncpg
import asyncpg_listen
import asyncio
import json
# from db_password import host as HOST, password_railway as PASSWORD_RAILWAY
from functools import partial
from telegram import Bot
# from key import TG_TOKEN_ADMIN
TG_TOKEN_ADMIN = os.getenv('TG_TOKEN_ADMIN')
HOST = os.getenv('HOST')
PASSWORD_RAILWAY = os.getenv('RAILWAY')


async def send_to_admin(username, order_id, order_time, ship_adress, bot):
    text = f'Покупатель с ником: @{username}\n' \
           f'Cделал заказ № {order_id}\n' \
           f'{order_time}\n' \
           f'Адрес доставки: {ship_adress}\n' \
           f'Полная информация в Базе данных.'
    await bot.send_message(text=text, chat_id=106683136)
    await bot.send_message(text=text, chat_id=186027538)


async def handle_notifications(notification, bot):
    print(notification)
    try:
        order = json.loads(notification.payload)
    except AttributeError:
        return
    except Exception as ex:
        print(ex.__class__)
        return
    customer_id = order["customer_id"]
    order_id = order["order_id"]
    order_time = order['order_time']
    ship_address = order['ship_adress']
    order_time = f'Дата: {order_time[:10]} Время: {order_time[11:19]}'
    conn = await asyncpg.connect(database='railway', user='postgres', port=5522, host=HOST,
                                 password=PASSWORD_RAILWAY)
    username = await conn.fetchval('SELECT username FROM customer WHERE customer_id = $1', customer_id)
    await send_to_admin(username, order_id, order_time, ship_address, bot)


async def main():
    bot = Bot(TG_TOKEN_ADMIN)
    listener = asyncpg_listen.NotificationListener(asyncpg_listen.connect_func(
        database='railway', user='postgres', port=5522, host=HOST,
        password=PASSWORD_RAILWAY))
    listener_task = asyncio.create_task(
        listener.run(
            {"orders": partial(handle_notifications, bot=bot)},
            policy=asyncpg_listen.ListenPolicy.ALL,
            notification_timeout=10
        )
    )
    await listener_task


if __name__ == '__main__':
    asyncio.run(main())

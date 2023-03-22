# import asyncpg
import asyncpg_listen
from db_password import password_railway, host
import asyncio
import json
from functools import partial
from telegram import Bot
from key import key_admin as key


async def send_to_admin(username, order_id, order_time, bot):
    text = f'Покупатель с id: {username}\nCделал заказ № {order_id}\n' \
           f'{order_time}\n' \
           f'Полная информация в Базе данных.'
    await bot.send_message(text=text, chat_id=106683136)


async def handle_notifications(notification, bot):
    print(notification)
    try:
        order = json.loads(notification.payload)
    except:
        return
    customer_id = order["customer_id"]
    order_id = order["order_id"]
    order_time = order['order_time']
    order_time = f'Дата: {order_time[:10]} Время: {order_time[11:19]}'
    username = customer_id
    await send_to_admin(username, order_id, order_time, bot)


async def main():
    bot = Bot(key)
    listener = asyncpg_listen.NotificationListener(asyncpg_listen.connect_func(
        database='railway', user='postgres', port=5522, host=host,
        password=password_railway))
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

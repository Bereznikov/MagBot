import logging
import time
import asyncio
import psycopg2
import random
from key import key
from customer import Customer
from db_password import host, password_railway

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Привет, {update.effective_user.username}')


async def helper(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f'Не жди помощи, {update.effective_user.first_name}')


async def echo(update, context):
    await update.message.reply_text(update.message.text)


async def zara_link(update, context):
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            select_query = """ SELECT product_link FROM product WHERE shop_id = 1 LIMIT 100"""
            cur.execute(select_query)
            records = cur.fetchall()
            tmp = records[random.randint(0, 100)][0]
            await update.message.reply_text(tmp)


async def zara_image(update, context):
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            select_query = """ SELECT product_link, image_link, product_name,price FROM product WHERE shop_id = 1 LIMIT 500 """
            cur.execute(select_query)
            records = cur.fetchall()
            for rand_int in range(random.randint(350, 400), random.randint(401, 450)):
                if rand_int % 2 == 3:
                    await asyncio.sleep(10)
                product_link = records[rand_int][0]
                image_link = records[rand_int][1]
                product_name = records[rand_int][2]
                price = records[rand_int][3]
                print(product_link, image_link)
                text = f"<a href='{image_link}'>картинка</a>"
                # await update.message.reply_text(message.chat.id, text, parse_mode='MarkdownV2')
                # await update.message.reply_text(text, )
                # await update.message.reply_text(image_link)
                await update.message.reply_markdown_v2(text=f"[l]({image_link})"
                                                            f" [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})")


if __name__ == '__main__':
    application = ApplicationBuilder().token(key).build()

    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', helper)
    zara_handler = CommandHandler('zara', zara_link)
    zara_image_handler = CommandHandler('image', zara_image)
    application.add_handler(zara_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(zara_image_handler)

    # application.add_handler(MessageHandler(filters.TEXT, zara_link))

    application.run_polling()

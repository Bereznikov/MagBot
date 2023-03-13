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


async def woman_dress(update, context):
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            count_query = "SELECT COUNT(*) FROM product WHERE category_id = '2187655'"
            cur.execute(count_query)
            number_of_products = cur.fetchone()[0]
            rand_dress = random.randint(1, number_of_products)
            select_query = """ SELECT product_link, image_link, product_name,price FROM product WHERE category_id = '2187655' LIMIT 1 OFFSET (%s)"""
            cur.execute(select_query, (rand_dress,))
            records = cur.fetchall()
            for rand_int in range(0, 1):
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


async def random_product(update, context):
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            rand_store = random.randint(1, 2)
            count_query = "SELECT COUNT(*) FROM product WHERE shop_id = (%s)"
            cur.execute(count_query, (rand_store,))
            shop_products = cur.fetchone()[0]
            rand_product = random.randint(1, shop_products)
            select_query = """ SELECT product_link, image_link, product_name,price FROM product WHERE shop_id = %s LIMIT 1 OFFSET %s"""
            cur.execute(select_query, (rand_store, rand_product,))
            records = cur.fetchall()
            for rand_int in range(0, 1):
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
    woman_dress_handler = CommandHandler('dress', woman_dress)
    random_product_handler = CommandHandler('random', random_product)
    application.add_handler(woman_dress_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(random_product_handler)

    # application.add_handler(MessageHandler(filters.TEXT, zara_link))

    application.run_polling()

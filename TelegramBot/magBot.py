import logging
import time
import asyncio
import psycopg2
import random
from key import key
from customer import Customer
from db_password import host, password_railway
from telegram import *
# Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import *

# ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SHOP, SECTION, DATABASE, SELECTION, RESTART = range(5)

USERS = {}


async def start(update, context):
    reply_keyboard = [["Zara", "Next", "От тети Глаши"]]
    await update.message.reply_text(
        f"Добро пожаловать в бот для покупки вещей ЯБерезка, {update.effective_user.username} \n"
        "Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
            input_field_placeholder="название магазина"
        ),
    )
    return SHOP


async def shop_name(update, context):
    user = update.message.from_user
    logger.info("Shop name %s: %s", user.first_name, update.message.text)
    if update.message.text == "От тети Глаши":
        await update.message.reply_text(f"Ха-ха, такого магазина нет, {user.first_name}. Ну ты и дурачок... \n"
                                        f"Начать заново /start")
    USERS[user.id] = [update.message.text]
    reply_keyboard = [["Мужчины", "Женщины", "Малыши"]]
    await update.message.reply_text(
        'Отлично, теперь скажите для кого ищете одежду?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
            input_field_placeholder="для кого?"))
    return SECTION


async def you_stupid(update, context):
    user = update.message.from_user
    logger.info("%s попался на тетю Глашу, вот лошара", user.first_name)
    await update.message.reply_text(
        f"Ха-ха, такого магазина нет, {user.first_name}. Ну ты и дурачок... \n",
        reply_markup=ReplyKeyboardMarkup(
            [['Выбрать заново']], one_time_keyboard=True, resize_keyboard=True))
    return SELECTION


async def section_name(update, context):
    user = update.message.from_user
    logger.info("Section name %s: %s", user.first_name, update.message.text)
    await update.message.reply_text("Отлично. Сейчас отправим вам варианты товаров.")
    return DATABASE


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
    user = update.message.from_user
    if update.message.text != 'Показать еще':
        USERS[user.id].append(update.message.text)
    logger.info("%s начал искать: %s", user.first_name, USERS[user.id])
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            store_name = USERS[user.id][0]
            section_name = USERS[user.id][1]
            count_query = """SELECT COUNT(*)
                            FROM product p
                            JOIN category c USING(category_id)
                            JOIN section se USING(section_id)
                            JOIN shop sh USING(shop_id)
                            WHERE sh.shop_name = %s AND se.section_name = %s"""
            cur.execute(count_query, (store_name, section_name))
            number_of_products = cur.fetchone()[0]
            rand_product = random.randint(1, number_of_products)
            select_query = """SELECT p.product_link, p.image_link, p.product_name, p.price
                            FROM product p
                            JOIN category c USING(category_id)
                            JOIN section se USING(section_id)
                            JOIN shop sh USING(shop_id)
                            WHERE sh.shop_name = %s AND se.section_name = %s
                            LIMIT 1 OFFSET %s"""

            cur.execute(select_query, (store_name, section_name, rand_product))
            records = cur.fetchone()
            product_link = records[0]
            image_link = records[1]
            product_name = records[2]
            price = records[3]
            logger.info("%s: %s, %s", user.first_name, USERS[user.id], product_name)
            # text = f"<a href='{image_link}'>картинка</a>"
            await update.message.reply_markdown_v2(
                text=f"[l]({image_link}) [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})",
                reply_markup=ReplyKeyboardMarkup([["Показать еще", 'Выбрать заново']],
                                                 one_time_keyboard=True, resize_keyboard=True),
            )
            return SELECTION


if __name__ == '__main__':
    application = ApplicationBuilder().token(key).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SHOP: [MessageHandler(filters.Regex("^(Zara|Next)$"), shop_name),
                   MessageHandler(filters.Regex("^(От тети Глаши)$"), you_stupid)],
            SECTION: [MessageHandler(filters.Regex("^(Мужчины|Женщины|Малыши)$"), random_product)],
            SELECTION: [MessageHandler(filters.Regex("^(Показать еще)$"), random_product),
                        MessageHandler(filters.Regex("^(Выбрать заново)$"), start)],
            # DATABASE: [MessageHandler(, random_product)]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    application.add_handler(conv_handler)
    help_handler = CommandHandler('help', helper)
    woman_dress_handler = CommandHandler('dress', woman_dress)
    random_product_handler = CommandHandler('random', random_product)
    application.add_handler(woman_dress_handler)
    # application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(random_product_handler)

    # application.add_handler(MessageHandler(filters.TEXT, zara_link))

    application.run_polling()

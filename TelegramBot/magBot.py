import logging
import time

import psycopg2
import psycopg2.extras
import random
import copy
from pprint import pprint
from functools import partial
from datetime import datetime, timezone
from key import key
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

SHOP, SECTION, DATABASE, SELECTION, CATEGORY, RESTART = range(6)

USERS = {}
START_STATE = {
    'shop': None,
    'section': None,
    'category': None,
    'number': 1,
    'cart': None,
    'products_from_category': None,
    'current_product_id': None
}


async def start(update, context):
    USERS[update.effective_user.id] = copy.deepcopy(START_STATE)
    reply_keyboard = [["Zara", "Next", "От тети Глаши"]]
    await update.message.reply_text(
        f"Добро пожаловать в бот для покупки вещей ЯБерезка, {update.effective_user.username} \n"
        "Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=reply_keyboard, resize_keyboard=True,
            input_field_placeholder="название магазина"
        ),
    )
    return SHOP


async def restart(update, context):
    reply_keyboard = [["Zara", "Next", "От тети Глаши"]]
    await update.message.reply_text(
        f"Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=reply_keyboard, resize_keyboard=True,
            input_field_placeholder="название магазина"
        ),
    )
    return SHOP


async def shop_name(update, context):
    user = update.message.from_user
    logger.info("Shop name %s: %s", user.first_name, update.message.text)
    USERS[user.id]['shop'] = update.message.text
    reply_keyboard = [["Мужчины 👨", "Женщины 👩"], ["Мальчики 👦", "Девочки 👧", "Малыши 👶"]]
    if update.message.text == "Next":
        reply_keyboard[1].append("Для дома 🏠")
    await update.message.reply_text(
        'Отлично, теперь скажите для кого ищете одежду?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, resize_keyboard=True,
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


class PostgresConnection:
    def __init__(self):
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                                      password=password_railway)
        connection.autocommit = True
        self.connection = connection

    def update(self):
        connection = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                                      password=password_railway)
        connection.autocommit = True
        self.connection = connection


def make_connection():
    conn = psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                            password=password_railway)
    conn.autocommit = True
    return conn


async def category_name(update, context, conn):
    print(conn.connection, conn.connection.closed)
    if conn.connection.closed != 0:
        conn.update()
    conn = conn.connection
    user = update.message.from_user
    USERS[user.id]['section'] = update.message.text[:-2]
    logger.info("%s выбрал секцию: %s", user.first_name, USERS[user.id]['section'])
    # with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
    #                       password=password_railway) as conn:
    with conn.cursor() as cur:
        store_name = USERS[user.id]['shop']
        section_name = USERS[user.id]['section']
        popular_categories_query = """SELECT category_name
                                            FROM product_full_info
                                            WHERE shop_name = %s AND section_name = %s
                                            GROUP BY category_name
                                            ORDER BY COUNT(*) DESC
                                            """
        cur.execute(popular_categories_query, (store_name, section_name))
        _tmp = cur.fetchall()
        _popular_categories = [a[0].title() for a in _tmp[:12]]
        popular_categories = [_popular_categories[:3], _popular_categories[3: 6],
                              _popular_categories[6:9], _popular_categories[9:]]
        await update.message.reply_text(
            'Хорошо, а из какой категории товаров?',
            reply_markup=ReplyKeyboardMarkup(
                popular_categories, resize_keyboard=True,
                input_field_placeholder="категория"))

    return CATEGORY


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
            await update.message.reply_markdown_v2(text=f"[l]({image_link})"
                                                        f" [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})")


async def show_product(update, context, conn):
    print(conn.connection, conn.connection.closed)
    if conn.connection.closed != 0:
        conn.update()
    conn = conn.connection
    user = update.message.from_user
    USERS[user.id]['current_product_id'] = None
    if update.message.text not in ('➡', '⬅'):
        USERS[user.id]['category'] = update.message.text.upper()
        USERS[user.id]['number'] = 1
        USERS[user.id]['product_from_category'] = None
    elif update.message.text == '➡':
        USERS[user.id]['number'] += 1
    elif USERS[user.id]['number'] > 1:
        USERS[user.id]['number'] -= 1
    logger.info("%s начал искать: %s", user.first_name, USERS[user.id]['category'])
    reply_keyboard = [["➡"], ['Выбрать заново', 'Добавить в корзину']]

    if USERS[user.id]['number'] > 1:
        reply_keyboard[0].insert(0, '⬅')
    if USERS[user.id]['cart']:
        reply_keyboard.append(['Оформить заказ'])

    if USERS[user.id]['product_from_category']:
        number = USERS[user.id]['number'] - 1
        image_link = USERS[user.id]['product_from_category'][number]['image_link']
        product_name = USERS[user.id]['product_from_category'][number]['product_name']
        price = USERS[user.id]['product_from_category'][number]['price']
        product_link = USERS[user.id]['product_from_category'][number]['product_link']
        await update.message.reply_markdown_v2(
            text=f"[l]({image_link}) [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                             resize_keyboard=True),
        )
        return SELECTION

    with conn.cursor() as cur:
        store_name = USERS[user.id]['shop']
        section_name = USERS[user.id]['section']
        category_name = USERS[user.id]['category']
        select_query = """SELECT product_link, image_link, product_name, price, product_id
                            FROM product_full_info
                            WHERE shop_name = %s AND section_name = %s AND category_name = %s
                            ORDER BY product_id
                            LIMIT 50"""
        cur.execute(select_query, (store_name, section_name, category_name,))
        records = cur.fetchall()
        USERS[user.id]['product_from_category'] = []
        for number, record in enumerate(records):
            product_link, image_link, product_name, price, product_id = record
            USERS[user.id]['product_from_category'].append({
                'product_id': product_id,
                'product_name': product_name.capitalize(),
                'price': price,
                'image_link': image_link,
                'product_link': product_link
            })
    image_link = USERS[user.id]['product_from_category'][0]['image_link']
    product_name = USERS[user.id]['product_from_category'][0]['product_name']
    price = USERS[user.id]['product_from_category'][0]['price']
    product_link = USERS[user.id]['product_from_category'][0]['product_link']
    logger.info("%s рассматривает %s, %s", user.first_name, product_name, USERS[user.id]['current_product_id'])

    # text = f"<a href='{image_link}'>картинка</a>"
    await update.message.reply_markdown_v2(
        text=f"[l]({image_link}) [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                         resize_keyboard=True),
    )
    return SELECTION


async def add_product(update, context):
    user = update.message.from_user
    number = USERS[user.id]['number']
    product_id = USERS[user.id]['product_from_category'][number]['product_id']
    product_name = USERS[user.id]['product_from_category'][number]['product_name']
    price = USERS[user.id]['product_from_category'][number]['price']
    product_link = USERS[user.id]['product_from_category'][number]['product_link']

    # select_query = """SELECT product_name, product_id, product_link, price
    #                                         FROM product_full_info
    #                                         WHERE product_id = %s"""
    # cur.execute(select_query, (product_id,))
    # product_name, product_id, product_link, price = cur.fetchone()
    # product_name = product_name.capitalize()

    logger.info("%s добавил в корзину %s", user.first_name, product_name)
    if not USERS[user.id]['cart']:
        USERS[user.id]['cart'] = {}
    if product_id not in USERS[user.id]['cart']:
        USERS[user.id]['cart'][product_id] = {'name': product_name,
                                              'quantity': 1,
                                              'link': product_link,
                                              'price': price}
    else:
        USERS[user.id]['cart'][product_id]['quantity'] += 1

    reply_keyboard = [["➡"], ['Выбрать заново', 'Добавить в корзину'], ['Оформить заказ']]
    if USERS[user.id]['number'] > 1:
        reply_keyboard[0].insert(0, '⬅')
    await update.message.reply_text(f'Вы добавили {product_name} в корзину',
                                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))


async def checkout(update, context):
    user = update.message.from_user
    customer_id = user.id
    first_name = user.first_name
    last_name = user.last_name
    username = user.username
    logger.info("%s оформил заказ. Корзина: %s", user.first_name, USERS[user.id]['cart'])
    cart_ar = []
    order_detail = []
    total_price = 0
    for product in USERS[user.id]['cart']:
        product_id = product
        product = USERS[user.id]['cart'][product]
        order_detail.append((product_id, product["quantity"]))
        total_price += product["price"] * product['quantity']
        cart_ar.append(
            f'Название: {product["name"].capitalize()} \nЦена: {product["price"]}\nКоличество: {product["quantity"]}\n'
            f'Товар: {product["link"]}')
    cart = '\n\n'.join(cart_ar)
    USERS[user.id]['cart'] = None
    await update.message.reply_text(f'Ваш заказ оформлен! \n'
                                    f'Общая стоимость: {total_price} Тенге \n\n'
                                    f'{cart}',
                                    reply_markup=ReplyKeyboardMarkup([['Выбрать заново']], resize_keyboard=True))

    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            select_user_query = """SELECT customer_id FROM customer"""
            cur.execute(select_user_query)
            users = [user[0] for user in cur.fetchall()]
            if customer_id not in users:
                insert_user_query = """INSERT INTO customer (customer_id, first_name, last_name, username)
                        VALUES (%s, %s, %s, %s)"""
                cur.execute(insert_user_query, (customer_id, first_name, last_name, username,))

            insert_order_query = """INSERT INTO orders (customer_id, order_time, status_id, shipper_id) VALUES (%s, %s, %s, %s)"""
            date_time_now = datetime.now(timezone.utc)
            try:
                cur.execute(insert_order_query, (customer_id, date_time_now, 1, 1,))
            except Exception as ex:
                logger.info(ex)
            select_order_id_query = """SELECT MAX(order_id) FROM orders"""
            cur.execute(select_order_id_query)
            order_id = cur.fetchone()[0]
            order_detail = [(a[0], order_id, a[1]) for a in order_detail]
            insert_order_detail_query = """INSERT INTO order_detail (product_id, order_id, quantity) VALUES (%s, %s, %s)"""
            psycopg2.extras.execute_batch(cur, insert_order_detail_query, order_detail)
    return SELECTION


if __name__ == '__main__':
    conn = PostgresConnection()
    print(conn.connection)
    application = ApplicationBuilder().token(key).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SHOP: [MessageHandler(filters.Regex("^(Zara|Next)$"), shop_name),
                   MessageHandler(filters.Regex("^(От тети Глаши)$"), you_stupid)],
            SECTION: [
                MessageHandler(filters.Regex("^(Мужчины 👨|Женщины 👩|Девочки 👧|Мальчики 👦|Малыши 👶|Для дома 🏠)$"),
                               partial(category_name, conn=conn))],
            CATEGORY: [MessageHandler(filters.TEXT, partial(show_product, conn=conn))],
            SELECTION: [MessageHandler(filters.Regex("^(Оформить заказ)$"), checkout),
                        MessageHandler(filters.Regex("^(Добавить в корзину)$"), add_product),
                        MessageHandler(filters.Regex("^(➡|⬅)$"), partial(show_product, conn=conn)),
                        MessageHandler(filters.Regex("^(Выбрать заново|)$"), restart)],
            # RESTART: [MessageHandler(filters.TEXT, restart)]
            # DATABASE: [MessageHandler(, random_product)]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    application.add_handler(conv_handler)

    application.run_polling()

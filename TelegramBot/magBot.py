import logging
import asyncio
# import time
from customer import Customer, ActiveCustomers
import psycopg2
import psycopg2.extras
import random
import copy
# from pprint import pprint
from functools import partial
from datetime import datetime, timezone
from key import key
from db_password import host, password_railway
from telegram import *
# Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import *
from db_connection import PostgresConnection

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


async def start(update, context, active_customers):
    user = update.effective_user
    new_customer = Customer(user.id, user.first_name, user.last_name, user.username)
    new_customer.state = copy.deepcopy(START_STATE)
    active_customers.add_customer(new_customer)
    reply_keyboard = [["Zara", "Next", "От тети Глаши"]]
    await update.message.reply_text(
        f"Добро пожаловать в бот для покупки вещей ЯБерезка, {new_customer.username} \n"
        "Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=reply_keyboard, resize_keyboard=True,
            input_field_placeholder="название магазина"
        ),
    )
    return SHOP


async def restart(update, context, active_customers):
    user = update.effective_user
    active_customers.customers[user.id].state = copy.deepcopy(START_STATE)
    reply_keyboard = [["Zara", "Next", "От тети Глаши"]]
    await update.message.reply_text(
        f"Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=reply_keyboard, resize_keyboard=True,
            input_field_placeholder="название магазина"
        ),
    )
    return SHOP


async def shop_name(update, context, active_customers):
    user = update.message.from_user
    logger.info("Shop name %s: %s", user.first_name, update.message.text)
    active_customers.customers[user.id].state['shop'] = update.message.text
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
        f"Ну сколько можно тыкать на Глашу, {user.first_name}? Ты точно нужным делом занимаешься?... \n",
        reply_markup=ReplyKeyboardMarkup(
            [['Выбрать заново']], resize_keyboard=True))
    return SELECTION


async def category_name(update, context, active_customers):
    active_customers.connection.check_connection()
    pg_connection = active_customers.connection
    user = update.message.from_user

    customer = active_customers.customers[user.id]

    customer.state['section'] = update.message.text[:-2]
    active_customers.customers[user.id] = customer
    logger.info("%s выбрал секцию: %s", user.first_name, customer.state['section'])
    # with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
    #                       password=password_railway) as conn:
    with pg_connection.connection.cursor() as cur:
        store_name = customer.state['shop']
        section_name = customer.state['section']
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


async def show_product(update, context, active_customers):
    active_customers.connection.check_connection()
    pg_connection = active_customers.connection
    user = update.message.from_user

    customer = active_customers.customers[user.id]

    active_customers.customers[user.id].state['current_product_id'] = None
    if update.message.text not in ('➡', '⬅'):
        customer.state['category'] = update.message.text.upper()
        customer.state['number'] = 1
        customer.state['product_from_category'] = None
    elif update.message.text == '➡':
        customer.state['number'] += 1
    elif customer.state['number'] > 1:
        customer.state['number'] -= 1
    logger.info("%s начал искать: %s", user.first_name, customer.state['category'])

    active_customers.customers[user.id] = customer

    reply_keyboard = [["➡"], ['Выбрать заново', 'Добавить в корзину']]

    if customer.state['number'] > 1:
        reply_keyboard[0].insert(0, '⬅')
    if customer.state['cart']:
        reply_keyboard.append(['Оформить заказ'])

    if customer.state['product_from_category']:
        number = customer.state['number'] - 1
        image_link = customer.state['product_from_category'][number]['image_link']
        product_name = customer.state['product_from_category'][number]['product_name']
        price = customer.state['product_from_category'][number]['price']
        product_link = customer.state['product_from_category'][number]['product_link']
        await update.message.reply_markdown_v2(
            text=f"[l]({image_link}) [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                             resize_keyboard=True),
        )
        return SELECTION

    with pg_connection.connection.cursor() as cur:
        store_name = customer.state['shop']
        section_name = customer.state['section']
        category_name = customer.state['category']
        select_query = """SELECT product_link, image_link, product_name, price, product_id
                            FROM product_full_info
                            WHERE shop_name = %s AND section_name = %s AND category_name = %s
                            ORDER BY product_id
                            LIMIT 50"""
        cur.execute(select_query, (store_name, section_name, category_name,))
        records = cur.fetchall()
        customer.state['product_from_category'] = []
        for number, record in enumerate(records):
            product_link, image_link, product_name, price, product_id = record
            active_customers.customers[user.id].state['product_from_category'].append({
                'product_id': product_id,
                'product_name': product_name.capitalize(),
                'price': price,
                'image_link': image_link,
                'product_link': product_link
            })
        active_customers.customers[user.id] = customer
    image_link = customer.state['product_from_category'][0]['image_link']
    product_name = customer.state['product_from_category'][0]['product_name']
    price = customer.state['product_from_category'][0]['price']
    product_link = customer.state['product_from_category'][0]['product_link']
    logger.info("%s рассматривает %s, %s", user.first_name, product_name,
                customer.state['current_product_id'])

    # text = f"<a href='{image_link}'>картинка</a>"
    await update.message.reply_markdown_v2(
        text=f"[l]({image_link}) [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                         resize_keyboard=True),
    )
    return SELECTION


async def add_product(update, context, active_customers):
    user = update.message.from_user
    customer = active_customers.customers[user.id]
    number = customer.state['number']
    product_id = customer.state['product_from_category'][number]['product_id']
    product_name = customer.state['product_from_category'][number]['product_name']
    price = customer.state['product_from_category'][number]['price']
    product_link = customer.state['product_from_category'][number]['product_link']

    logger.info("%s добавил в корзину %s", user.first_name, product_name)
    if not customer.state['cart']:
        customer.state['cart'] = {}
    if product_id not in active_customers.customers[user.id].state['cart']:
        customer.state['cart'][product_id] = {'name': product_name,
                                              'quantity': 1,
                                              'link': product_link,
                                              'price': price}
    else:
        customer.state['cart'][product_id]['quantity'] += 1
    active_customers.customers[user.id] = customer

    reply_keyboard = [["➡"], ['Выбрать заново', 'Добавить в корзину'], ['Оформить заказ']]
    if customer.state['number'] > 1:
        reply_keyboard[0].insert(0, '⬅')
    await update.message.reply_text(f'Вы добавили {product_name} в корзину',
                                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))


async def checkout(update, context, active_customers):
    user = update.message.from_user
    customer_id = user.id
    first_name = user.first_name
    last_name = user.last_name
    username = user.username
    logger.info("%s оформил заказ. Корзина: %s", user.first_name, active_customers.customers[user.id].state['cart'])
    cart_ar = []
    order_detail = []
    total_price = 0
    customer = active_customers.customers[user.id]
    for product in customer.state['cart']:
        product_id = product
        product = customer.state['cart'][product]
        order_detail.append((product_id, product["quantity"]))
        total_price += product["price"] * product['quantity']
        cart_ar.append(
            f'Название: {product["name"].capitalize()} \nЦена: {product["price"]}\nКоличество: {product["quantity"]}\n'
            f'Товар: {product["link"]}')
    cart = '\n\n'.join(cart_ar)
    active_customers.customers[user.id].state['cart'] = None
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
    connection = PostgresConnection()
    active_customers = ActiveCustomers(connection)
    # print(active_customers)
    application = ApplicationBuilder().token(key).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", partial(start, active_customers=active_customers))],
        states={
            SHOP: [
                MessageHandler(filters.Regex("^(Zara|Next)$"), partial(shop_name, active_customers=active_customers)),
                MessageHandler(filters.Regex("^(От тети Глаши)$"),
                               partial(you_stupid, active_customers=active_customers))],

            SECTION: [
                MessageHandler(filters.Regex("^(Мужчины 👨|Женщины 👩|Девочки 👧|Мальчики 👦|Малыши 👶|Для дома 🏠)$"),
                               partial(category_name, active_customers=active_customers))],

            CATEGORY: [MessageHandler(filters.TEXT, partial(show_product, active_customers=active_customers))],

            SELECTION: [MessageHandler(filters.Regex("^(Оформить заказ)$"),
                                       partial(checkout, active_customers=active_customers)),

                        MessageHandler(filters.Regex("^(Добавить в корзину)$"),
                                       partial(add_product, active_customers=active_customers)),

                        MessageHandler(filters.Regex("^(➡|⬅)$"),
                                       partial(show_product, active_customers=active_customers)),

                        MessageHandler(filters.Regex("^(Выбрать заново|)$"),
                                       partial(restart, active_customers=active_customers))],
        },
        fallbacks=[CommandHandler("start", partial(start, active_customers=active_customers))]
    )

    application.add_handler(conv_handler)

    application.run_polling()

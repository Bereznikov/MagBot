import logging
from customer import Customer
import psycopg2
import psycopg2.extras
import random
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


# def facts_to_str(user_data):
#     facts = [f"{key} - {value}" for key, value in user_data.items()]
#     return "\n".join(facts).join(["\n", "\n"])


async def start(update, context):
    user = update.effective_user
    pg_con = PostgresConnection()
    new_customer = Customer(user.id, user.first_name, user.last_name, user.username, connection=pg_con)
    context.user_data[user.id] = new_customer
    reply_keyboard = [["Zara", "Next", "От тети Глаши"]]
    await update.message.reply_text(
        f"Добро пожаловать в бот для покупки вещей ЯБерезка, {new_customer.username} \n"
        "Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, resize_keyboard=True,
                                         input_field_placeholder="Название магазина"),
    )
    return SHOP


async def restart(update, context):
    reply_keyboard = [["Zara", "Next", "От тети Глаши"]]
    await update.message.reply_text(
        f"Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, resize_keyboard=True,
                                         input_field_placeholder="название магазина"),
    )
    return SHOP


async def shop_name(update, context):
    user = update.message.from_user
    logger.info("Shop name %s: %s", user.first_name, update.message.text)
    context.user_data[user.id].shop = update.message.text
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
        f"Ну сколько можно тыкать на тетю Глашу, {user.first_name}? Ты точно нужным делом занимаешься?... \n",
        reply_markup=ReplyKeyboardMarkup(
            [['Выбрать заново']], resize_keyboard=True))
    return SELECTION


async def category_name(update, context):
    user = update.message.from_user
    context.user_data[user.id].section = update.message.text[:-2]

    logger.info("%s выбрал секцию: %s", user.first_name, update.message.text[:-2])
    context.user_data[user.id].connection.simple_check()
    with context.user_data[user.id].connection.connection.cursor() as cur:
        store_name = context.user_data[user.id].shop
        section_name = context.user_data[user.id].section
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


async def show_product(update, context):
    user = update.message.from_user
    context.user_data[user.id].curret_product_id = None
    customer = context.user_data[user.id]
    if update.message.text not in ('➡', '⬅'):
        customer.category = update.message.text.upper()
        customer.number = 1
        customer.product_from_category = None
    elif update.message.text == '➡':
        customer.number += 1
    elif customer.number > 1:
        customer.number -= 1
    context.user_data[user.id] = customer

    reply_keyboard = [["➡"], ['Выбрать заново', 'Добавить в корзину']]

    if customer.number > 1:
        reply_keyboard[0].insert(0, '⬅')
    if customer.cart:
        reply_keyboard.append(['Оформить заказ'])

    if customer.product_from_category and customer.number <= len(customer.product_from_category):
        number = customer.number - 1
        image_link = customer.product_from_category[number]['image_link']
        product_name = customer.product_from_category[number]['product_name']
        price = customer.product_from_category[number]['price']
        product_link = customer.product_from_category[number]['product_link']
        product_id = customer.product_from_category[number]['product_id']
        logger.info("%s рассматривает %s c id %s", user.first_name, product_name, product_id)
        await update.message.reply_markdown_v2(
            text=f"[l]({image_link}) [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                             resize_keyboard=True),
        )
        return SELECTION
    context.user_data[user.id].connection.simple_check()
    with context.user_data[user.id].connection.connection.cursor() as cur:
        store_name = customer.shop
        section_name = customer.section
        category_name = customer.category
        offset = 0
        if customer.product_from_category:
            offset = len(customer.product_from_category)

        select_query = """SELECT product_link, image_link, product_name, price, product_id
                            FROM product_full_info
                            WHERE shop_name = %s AND section_name = %s AND category_name = %s
                            ORDER BY product_id
                            LIMIT 10
                            OFFSET %s"""
        cur.execute(select_query, (store_name, section_name, category_name, offset))
        records = cur.fetchall()
        if not context.user_data[user.id].product_from_category:
            context.user_data[user.id].product_from_category = []
        for number, record in enumerate(records):
            product_link, image_link, product_name, price, product_id = record
            context.user_data[user.id].product_from_category.append({
                'product_id': product_id,
                'product_name': product_name.capitalize(),
                'price': price,
                'image_link': image_link,
                'product_link': product_link
            })
    product_link, image_link, product_name, price, product_id = records[0]
    product_name = product_name.capitalize()
    logger.info("%s рассматривает %s c id %s", user.first_name, product_name, product_id)

    await update.message.reply_markdown_v2(
        text=f"[l]({image_link}) [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True),
    )
    return SELECTION


async def add_product(update, context):
    user = update.message.from_user
    customer = context.user_data[user.id]
    number = customer.number - 1
    product_id = customer.product_from_category[number]['product_id']
    product_name = customer.product_from_category[number]['product_name']
    price = customer.product_from_category[number]['price']
    product_link = customer.product_from_category[number]['product_link']

    logger.info("%s добавил в корзину %s c id %s", user.first_name, product_name, product_id)
    if not customer.cart:
        customer.cart = {}
    if product_id not in customer.cart:
        customer.cart[product_id] = {'name': product_name,
                                     'quantity': 1,
                                     'link': product_link,
                                     'price': price}
    else:
        customer.cart[product_id]['quantity'] += 1
    context.user_data[user.id] = customer

    reply_keyboard = [["➡"], ['Выбрать заново', 'Добавить в корзину'], ['Оформить заказ']]
    if customer.number > 1:
        reply_keyboard[0].insert(0, '⬅')
    await update.message.reply_text(f'Вы добавили {product_name} в корзину',
                                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))


async def checkout(update, context):
    user = update.message.from_user
    customer = context.user_data[user.id]

    logger.info("%s оформил заказ. Корзина: %s", customer.first_name, customer.cart)

    cart_messages = []
    total_price = 0
    for product in customer.cart.values():
        total_price += product["price"] * product["quantity"]
        cart_messages.append(
            f'Название: {product["name"].capitalize()} \nЦена: {product["price"]}\nКоличество: {product["quantity"]}\n'
            f'Товар: {product["link"]}')
    cart_messages = '\n\n'.join(cart_messages)
    message = f"Ваш заказ оформлен! \nОбщая стоимость: {total_price} Тенге \n\n {cart_messages}"

    await update.message.reply_text(message,
                                    reply_markup=ReplyKeyboardMarkup([['Выбрать заново']], resize_keyboard=True))

    context.user_data[user.id].connection.simple_check()
    with context.user_data[user.id].connection.connection.cursor() as cur:
        select_user_query = """SELECT customer_id FROM customer"""
        cur.execute(select_user_query)
        users = [user[0] for user in cur.fetchall()]
        if customer.id not in users:
            insert_user_query = """INSERT INTO customer (customer_id, first_name, last_name, username)
                            VALUES (%s, %s, %s, %s)"""
            cur.execute(insert_user_query, (customer.id, customer.first_name, customer.last_name, customer.username,))

        insert_order_query = """INSERT INTO orders (customer_id, order_time, status_id, shipper_id)
         VALUES (%s, %s, %s, %s)"""
        date_time_now = datetime.now(timezone.utc)
        try:
            cur.execute(insert_order_query, (customer.id, date_time_now, 1, 1,))
        except Exception as ex:
            logger.info(ex)
        select_order_id_query = """SELECT MAX(order_id) FROM orders"""
        cur.execute(select_order_id_query)
        order_id = cur.fetchone()[0]
        order_detail = []
        for p_id, product in customer.cart.items():
            order_detail.append((p_id, order_id, product["quantity"]))
        insert_order_detail_query = """INSERT INTO order_detail (product_id, order_id, quantity) VALUES (%s, %s, %s)"""
        psycopg2.extras.execute_batch(cur, insert_order_detail_query, order_detail)
        context.user_data[user.id].cart = None

    return SELECTION


if __name__ == '__main__':
    # my_persistence = PicklePersistence(filepath='my_file.pkl')
    my_persistence = DictPersistence()
    application = ApplicationBuilder().token(key).persistence(my_persistence).build()

    # application = ApplicationBuilder().token(key).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("s", start)],
        states={
            SHOP: [
                MessageHandler(filters.Regex("^(Zara|Next)$"), shop_name),
                MessageHandler(filters.Regex("^(От тети Глаши)$"), you_stupid)],

            SECTION: [
                MessageHandler(filters.Regex(
                    "^(Мужчины 👨|Женщины 👩|Девочки 👧|Мальчики 👦|Малыши 👶|Для дома 🏠)$"), category_name)],

            CATEGORY: [MessageHandler(filters.TEXT, show_product)],

            SELECTION: [MessageHandler(filters.Regex("^(Оформить заказ)$"), checkout),
                        MessageHandler(filters.Regex("^(Добавить в корзину)$"), add_product),
                        MessageHandler(filters.Regex("^(➡|⬅)$"), show_product),
                        MessageHandler(filters.Regex("^(Выбрать заново|)$"), restart)],
        },
        fallbacks=[CommandHandler("start", start)],
        persistent=True,
        name='magbot',
    )

    application.add_handler(conv_handler)

    application.run_polling()

import logging
import psycopg2
import psycopg2.extras
import random
import traceback
import html
import json
from customer import Customer
from db_connection import PostgresConnection
from key import key
from datetime import datetime, timezone
from db_password import host, password_railway
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, \
    InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, \
    CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SHOP, SECTION, SELECTION, CATEGORY, RESTART, ADDRESS, CHECKOUT, CART = range(8)


async def start(update, context):
    user = update.effective_user
    reply_keyboard = [["Zara", "Next", "От тети Глаши"]]
    logger.info('%s стартанул бота', user.first_name)
    await update.message.reply_text(
        f"Добро пожаловать в бот для покупки вещей ЯБерезка, {user.username} \n"
        "Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, resize_keyboard=True),
    )
    pg_con = PostgresConnection()
    new_customer = Customer(user.id, user.first_name, user.last_name, user.username, connection=pg_con)
    context.user_data[user.id] = new_customer
    return SHOP


async def restart(update, context):
    reply_keyboard = [["Zara", "Next", "От тети Глаши"]]
    await update.message.reply_text(
        f"Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, resize_keyboard=True))
    return SHOP


async def shop_name(update, context):
    user = update.message.from_user
    logger.info("%s выбрал магазин %s", user.first_name, update.message.text)
    context.user_data[user.id].shop = update.message.text
    reply_keyboard = [["Мужчины 👨", "Женщины 👩"], ["Мальчики 👦", "Девочки 👧", "Малыши 👶"]]
    if update.message.text == "Next":
        reply_keyboard[1].append("Для дома 🏠")
    await update.message.reply_text(
        'Отлично, теперь скажите для кого ищете одежду?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, resize_keyboard=True))
    return SECTION


async def you_silly(update, context):
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
                popular_categories, resize_keyboard=True))

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
            select_query = """ 
            SELECT product_link, image_link, product_name,price
            FROM product
            WHERE category_id = '2187655'
            LIMIT 1 OFFSET (%s)"""
            cur.execute(select_query, (rand_dress,))
            records = cur.fetchall()
            for rand_int in range(0, 1):
                product_link = records[rand_int][0]
                image_link = records[rand_int][1]
                product_name = records[rand_int][2]
                price = records[rand_int][3]
                print(product_link, image_link)
            await update.message.reply_markdown_v2(text=f"[l]({image_link})"
                                                        f" [{product_name.replace('-', ' ').replace('.', ' ')} "
                                                        f"{price} тг]({product_link})")


async def show_product(update, context):
    user = update.message.from_user
    customer = context.user_data[user.id]
    if update.message.text not in ('➡', '⬅'):
        context.user_data[user.id].category = update.message.text.upper()
        context.user_data[user.id].number = 0
        context.user_data[user.id].products_from_category = []
        await show_product_sql_products(context, user)
        customer = context.user_data[user.id]

    elif update.message.text == '➡':
        if customer.number + 2 >= len(customer.products_from_category):
            await show_product_sql_products(context, user)
        customer.number = min(customer.number + 1, customer.number_of_products - 1)
    elif update.message.text == '⬅':
        customer.number = max(customer.number - 1, 0)

    reply_keyboard = await show_product_keyboard(context.user_data[user.id])

    number = customer.number
    if customer.products_from_category is None or number >= len(customer.products_from_category):
        logger.exception("%s customer.products_from_category is None %s, %s", user.first_name, number,
                         customer.products_from_category)
        return SELECTION

    image_link = customer.products_from_category[number]['image_link']
    product_name = customer.products_from_category[number]['product_name']
    price = customer.products_from_category[number]['price']
    product_link = customer.products_from_category[number]['product_link']
    product_id = customer.products_from_category[number]['product_id']
    product_name = product_name.capitalize()
    logger.info("%s рассматривает %s c id %s", user.first_name, product_name, product_id)
    product_name = product_name.replace('-', "\-").replace('.', '\.')
    await update.message.reply_photo(image_link,
                                     caption=f"{product_name}\n"
                                             f"Цена: {price} Тенге\n"
                                             f"[Ссылка на товар]({product_link})",
                                     parse_mode='MarkdownV2',
                                     reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True),
                                     )
    return SELECTION


async def show_product_sql_products(context, user):
    customer = context.user_data[user.id]
    customer.connection.simple_check()
    with customer.connection.connection.cursor() as cur:
        select_query = """
                    SELECT product_link, image_link, product_name, price, product_id
                    FROM product_full_info
                    WHERE shop_name = %s AND section_name = %s AND category_name = %s
                    ORDER BY product_id
                    LIMIT 10
                    OFFSET %s
                    """
        cur.execute(select_query,
                    (customer.shop, customer.section,
                     customer.category, len(customer.products_from_category)))
        records = cur.fetchall()
        for number, record in enumerate(records):
            product_link, image_link, product_name, price, product_id = record
            customer.products_from_category.append({
                'product_id': product_id,
                'product_name': product_name.capitalize(),
                'price': price,
                'image_link': image_link,
                'product_link': product_link
            })
        customer.number_of_products = len(context.user_data[user.id].products_from_category)
        context.user_data[user.id] = customer


async def show_product_keyboard(customer):
    reply_keyboard = [[],
                      ['Добавить в корзину'],
                      ['Выбрать заново']]
    if customer.number > 0:
        reply_keyboard[0].append('⬅')
    if customer.number + 1 < customer.number_of_products:
        reply_keyboard[0].append('➡')
    if customer.cart and customer.products_from_category:
        for i, product in enumerate(customer.cart):
            if customer.products_from_category[customer.number]['product_id'] == product['product_id']:
                reply_keyboard[1] = ['➖', f"{customer.cart[i]['quantity']}", '➕']
    if customer.cart:
        reply_keyboard[-1].insert(0, 'Корзина')
    return reply_keyboard


async def show_product_query(update, context):
    user = update.callback_query.from_user
    context.user_data[user.id].curret_product_id = None
    customer = context.user_data[user.id]
    reply_keyboard = await show_product_keyboard(customer)
    number = customer.number
    if customer.products_from_category is None or number >= len(customer.products_from_category):
        logger.exception("%s customer.products_from_category is None", user.first_name)
        return SELECTION
    image_link = customer.products_from_category[number]['image_link']
    product_name = customer.products_from_category[number]['product_name']
    price = customer.products_from_category[number]['price']
    product_link = customer.products_from_category[number]['product_link']
    product_id = customer.products_from_category[number]['product_id']
    product_name = product_name.capitalize()

    logger.info("%s Вышел из корзины и рассматривает %s c id %s", user.first_name, product_name, product_id)

    product_name = product_name.replace('-', '\-').replace('.', '\.')
    await update.callback_query.message.reply_photo(image_link,
                                                    caption=f"{product_name}\n"
                                                            f"Цена: {price} Тенге\n"
                                                            f"[Ссылка на товар]({product_link})",
                                                    parse_mode='MarkdownV2',
                                                    reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                                                     resize_keyboard=True),
                                                    )
    return SELECTION


async def add_product(update, context):
    user = update.message.from_user
    customer = context.user_data[user.id]
    number = customer.number
    product_id = customer.products_from_category[number]['product_id']
    product_name = customer.products_from_category[number]['product_name']
    price = customer.products_from_category[number]['price']
    product_link = customer.products_from_category[number]['product_link']
    image_link = customer.products_from_category[number]['image_link']

    logger.info("%s добавил в корзину %s c id %s", user.first_name, product_name, product_id)
    if not customer.cart:
        customer.cart = []

    deleted_from_cart = False

    for i, product in enumerate(customer.cart):
        if product['product_id'] == product_id:
            if update.message.text == '➖':
                customer.cart[i]['quantity'] -= 1
                if customer.cart[i]['quantity'] <= 0:
                    customer.cart.pop(i)
                    deleted_from_cart = True
            else:
                customer.cart[i]['quantity'] += 1
            product_num = i
            break
    else:
        product_num = len(customer.cart)
        customer.cart.append({
            'product_id': product_id,
            'name': product_name,
            'quantity': 1,
            'link': product_link,
            'image_link': image_link,
            'price': price})

    reply_keyboard = await add_product_keyboard(customer, deleted_from_cart, product_num)
    await update.message.reply_text(f'Вы добавили {product_name} в корзину',
                                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))


async def add_product_keyboard(customer, deleted_from_cart, product_num):
    reply_keyboard = [[],
                      ['Добавить в корзину'],
                      ['Выбрать заново']]
    if customer.number > 0:
        reply_keyboard[0].append('⬅')
    if customer.number + 1 < customer.number_of_products:
        reply_keyboard[0].append('➡')
    if not deleted_from_cart and customer.cart[product_num]['quantity'] > 0:
        reply_keyboard[1] = ['➖', f"{customer.cart[product_num]['quantity']}", '➕']
    if customer.cart:
        reply_keyboard[-1].insert(0, 'Корзина')
    return reply_keyboard


async def address(update, context):
    user = update.callback_query.from_user
    customer = context.user_data[user.id]
    logger.info("%s начал оформлять заказ. Корзина: %s", customer.first_name, customer.cart)
    reply_markup = ReplyKeyboardRemove()
    if customer.address:
        reply_markup = ReplyKeyboardMarkup([[customer.address]], resize_keyboard=True)
    await update.callback_query.message.reply_text('Напишите адрес доставки', reply_markup=reply_markup)
    return ADDRESS


async def shipper(update, context):
    user = update.message.from_user
    context.user_data[user.id].address = update.message.text
    customer = context.user_data[user.id]
    logger.info("%s продолжил оформлять заказ. Корзина: %s", customer.first_name, customer.cart)
    await update.message.reply_text('Выберите фирму доставки',
                                    reply_markup=ReplyKeyboardMarkup([['СДЭК', 'Почта России']], resize_keyboard=True))
    return CHECKOUT


async def show_cart_message(update, context):
    user = update.message.from_user
    context.user_data[user.id].cart_position = 0
    customer = context.user_data[user.id]
    await update.message.reply_text('Ваша корзина:', reply_markup=ReplyKeyboardRemove())
    logger.info("%s смотрит корзину. Корзина: %s", customer.first_name, customer.cart)
    reply_keyboard = await show_cart_keyboard(customer)
    product = customer.cart[customer.cart_position]
    cart_messages = (
        f'{product["name"].capitalize()} \nЦена: {product["price"]}\n')
    await update.message.reply_photo(context.user_data[user.id].cart[0]["image_link"],
                                     caption=cart_messages, reply_markup=InlineKeyboardMarkup(reply_keyboard))
    return CART


async def show_cart_query(update, context):
    user = update.callback_query.from_user
    customer = context.user_data[user.id]
    query = update.callback_query
    if query.data == 'Cart>':
        customer.cart_position = min(customer.cart_position + 1, len(customer.cart) - 1)
    elif query.data == 'Cart<':
        customer.cart_position = max(customer.cart_position - 1, 0)
    elif query.data == 'Num+':
        customer.cart[customer.cart_position]['quantity'] += 1
    elif query.data == 'Num-':
        customer.cart[customer.cart_position]['quantity'] = \
            max(customer.cart[customer.cart_position]['quantity'] - 1, 0)
        if customer.cart[customer.cart_position]['quantity'] == 0:
            customer.cart.pop(customer.cart_position)
            customer.cart_position = 0
            if len(customer.cart) == 0:
                await update.callback_query.message.reply_text('Корзина пуста, начнем заново? /restart')
                return RESTART
    if query.data in ('Cart<', 'Cart>'):
        logger.info("%s перелистыват корзину. Корзина: %s", customer.first_name, customer.cart)
    elif query.data in ('Num-', 'Num+'):
        logger.info("%s изменил количество товара в корзине. Корзина: %s", customer.first_name, customer.cart)
    else:
        logger.info("%s что-то делает в корзине. Корзина: %s", customer.first_name, customer.cart)
    reply_keyboard = await show_cart_keyboard(customer)
    product = context.user_data[user.id].cart[customer.cart_position]
    cart_messages = (
        f'{product["name"].capitalize()} \nЦена: {product["price"]}\n')
    await query.edit_message_media(
        InputMediaPhoto(context.user_data[user.id].cart[customer.cart_position]["image_link"]),
        reply_markup=InlineKeyboardMarkup(reply_keyboard))

    await query.edit_message_caption(caption=cart_messages,
                                     reply_markup=InlineKeyboardMarkup(reply_keyboard))

    return CART


async def show_cart_keyboard(customer):
    reply_keyboard = [
        [
            InlineKeyboardButton("➖", callback_data='Num-'),
            InlineKeyboardButton(customer.cart[customer.cart_position]['quantity'], callback_data='Nothing'),
            InlineKeyboardButton("➕", callback_data='Num+')
        ],
        [
            InlineKeyboardButton("⬅", callback_data='Cart<'),
            InlineKeyboardButton(f'{customer.cart_position + 1} из {len(customer.cart)}', callback_data='Nothing'),
            InlineKeyboardButton("➡", callback_data='Cart>')
        ],
        [
            InlineKeyboardButton("Оформить заказ", callback_data='Order'),
            InlineKeyboardButton("Назад в меню", callback_data='Menu')
        ]
    ]
    return reply_keyboard


async def checkout(update, context):
    user = update.message.from_user
    context.user_data[user.id].shipper = update.message.text
    customer = context.user_data[user.id]
    logger.info("%s оформил заказ. Корзина: %s", customer.first_name, customer.cart)

    cart_messages = []
    total_price = 0
    for product in customer.cart:
        total_price += product["price"] * product["quantity"]
        product_name = product["name"].capitalize().replace("-", "\-").replace(".", "\.").replace('!', '\!')
        cart_messages.append(
            f'{product_name}\n'
            f'Цена: {product["price"]} Тенге\n'
            f'Количество: {product["quantity"]}\n'
            f'[Ссылка на товар]({product["link"]})')
    cart_messages = '\n\n'.join(cart_messages)
    message = f"Ваш заказ оформлен." \
              f"\nОбщая стоимость: {total_price} Тенге\n\n{cart_messages}"

    context.user_data[user.id].connection.simple_check()
    with context.user_data[user.id].connection.connection.cursor() as cur:
        try:
            select_user_query = """SELECT customer_id FROM customer"""
            cur.execute(select_user_query)
            users = [user[0] for user in cur.fetchall()]
            if customer.id not in users:
                insert_user_query = """INSERT INTO customer (customer_id, first_name, last_name, username)
                                VALUES (%s, %s, %s, %s)"""
                cur.execute(insert_user_query,
                            (user.id, user.first_name, user.last_name, user.username,))

            insert_order_query = """INSERT INTO orders (customer_id, order_time, ship_adress, status_id, shipper_id)
             VALUES (%s, %s, %s, %s, %s)"""
            date_time_now = datetime.now(timezone.utc)

            shipper_id = 1
            if customer.shipper == 'Почта России':
                shipper_id = 2
            cur.execute(insert_order_query, (customer.id, date_time_now, customer.address, 1, shipper_id,))
            select_order_id_query = """SELECT MAX(order_id) FROM orders"""
            cur.execute(select_order_id_query)
            order_id = cur.fetchone()[0]
            order_detail = []
            for product in customer.cart:
                order_detail.append((product['product_id'], order_id, product["quantity"]))
            insert_order_detail_query = """INSERT INTO order_detail (product_id, order_id, quantity)
             VALUES (%s, %s, %s)"""
            psycopg2.extras.execute_batch(cur, insert_order_detail_query, order_detail)
            logger.info("%s оформил заказ. Корзина: %s", customer.first_name, customer.cart)
            context.user_data[user.id].cart = None
            await update.message.reply_markdown_v2(message,
                                                   reply_markup=ReplyKeyboardMarkup([['Выбрать заново']],
                                                                                    resize_keyboard=True))
        except Exception as ex:
            logger.exception(ex)

    return SELECTION


async def error_handler(update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # logger.error(msg=message)
    await context.bot.send_message(chat_id=106683136, text=message, parse_mode="HTML")


if __name__ == '__main__':
    # my_persistence = PicklePersistence(filepath='my_file.pkl')
    # my_persistence = DictPersistence()
    # application = ApplicationBuilder().token(key).persistence(my_persistence).build()

    application = ApplicationBuilder().token(key).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("s", start)],
        states={
            RESTART: [CommandHandler('restart', restart)],
            SHOP: [
                # CallbackQueryHandler(shop_name, pattern="^(Zara|Next)$"),
                MessageHandler(filters.Regex("^(Zara|Next)$"), shop_name),
                MessageHandler(filters.Regex("^От тети Глаши$"), you_silly)],

            SECTION: [
                MessageHandler(filters.Regex(
                    "^(Мужчины|Женщины|Девочки|Мальчики|Малыши|Для дома)"), category_name)],

            CATEGORY: [MessageHandler(filters.TEXT, show_product)],

            SELECTION: [MessageHandler(filters.Regex("^Оформить заказ$"), address),
                        MessageHandler(filters.Regex("^Корзина$"), show_cart_message),
                        MessageHandler(filters.Regex("^(Добавить|➕|➖)"), add_product),
                        MessageHandler(filters.Regex("^(➡|⬅|Закрыть корзину)$"), show_product),
                        MessageHandler(filters.Regex("^(Выбрать заново|)$"), restart),
                        MessageHandler(filters.Regex('/^([^0-9]*)$/'), show_product)],
            CART: [CallbackQueryHandler(show_cart_query, pattern="^(Num|Nothing|Cart)"),
                   CallbackQueryHandler(show_product_query, pattern="^Menu$"),
                   CallbackQueryHandler(address, pattern="^Order$")],
            ADDRESS: [MessageHandler(filters.TEXT, shipper)],
            CHECKOUT: [MessageHandler(filters.Regex("^(СДЭК|Почта России)$"), checkout)]
        },
        fallbacks=[CommandHandler("start", start)],
        # persistent=True,
        name='magbot',
    )
    application.add_error_handler(error_handler)
    application.add_handler(conv_handler)
    application.run_polling()

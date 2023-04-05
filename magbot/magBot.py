import logging
import os

import psycopg2
import psycopg2.extras
# import traceback
# import html
# import json
from customer import Customer
from db_connection import PostgresConnection
# from key import key as TG_TOKEN_MAG
from datetime import datetime, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, \
    InputMediaPhoto
# Update
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
    reply_keyboard = [["Zara", "Next"]]
    logger.info('%s стартанул бота', user.first_name)
    await update.message.reply_text(
        f"Добро пожаловать в бот для покупки вещей из магазинов Zara и Next, {user.username} \n"
        "Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, resize_keyboard=True),
    )
    pg_con = PostgresConnection()
    new_customer = Customer(user.id, user.first_name, user.last_name, user.username, connection=pg_con)
    context.user_data[user.id] = new_customer
    return SHOP


async def restart(update, context):
    user = update.effective_user
    customer = context.user_data[user.id]
    await _db_check_with_logging(customer)
    reply_keyboard = [["Zara", "Next"]]
    logger.info('%s сделал restart бота', user.first_name)
    await update.message.reply_text(
        f"Из какого магазина хотите заказать одежду?",
        reply_markup=ReplyKeyboardMarkup(keyboard=reply_keyboard, resize_keyboard=True))
    return SHOP


async def section_name(update, context):
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


async def fake_shop(update, context):
    user = update.message.from_user
    logger.info("%s попался на тетю Глашу, вот лошара", user.first_name)
    await update.message.reply_text(
        f"Ого, как ты здесь оказался, {user.first_name}? Ты точно нужным делом занимаешься?... \n",
        reply_markup=ReplyKeyboardMarkup(
            [['Выбрать заново']], resize_keyboard=True))
    return SELECTION


async def category_name(update, context):
    user = update.message.from_user
    customer = context.user_data[user.id]
    customer.section = update.message.text[:-2]

    logger.info("%s выбрал секцию: %s", user.first_name, update.message.text[:-2])
    await _db_check_with_logging(customer)
    with customer.connection.connection.cursor() as cur:
        store_name = context.user_data[user.id].shop
        sections_name = context.user_data[user.id].section
        popular_categories_query = """
        SELECT category_name
        FROM product_full_info
        WHERE shop_name = %s AND section_name = %s AND availability = true
        GROUP BY category_name
        ORDER BY COUNT(*) DESC"""
        cur.execute(popular_categories_query, (store_name, sections_name))
        all_categories = cur.fetchall()
        flat_categories = [a[0].capitalize() for a in all_categories[:30]]
        popular_categories = [flat_categories[2 * i: 2 * i + 2] for i in range((len(flat_categories) + 1) // 2)]
        await update.message.reply_text(
            'Хорошо, а из какой категории товаров?',
            reply_markup=ReplyKeyboardMarkup(
                popular_categories, resize_keyboard=True))

    return CATEGORY


async def _db_check_with_logging(customer):
    is_connection_updated = customer.connection.strong_check()
    if is_connection_updated:
        logger.info('у пользователя %s обновилось соединение с БД', customer.first_name)


async def show_product(update, context):
    user = update.message.from_user
    customer = context.user_data[user.id]
    if update.message.text not in ('➡', '⬅'):
        customer.category = update.message.text.upper()
        customer.number = 0
        customer.products_from_category = []
        await _show_product_sql(customer)
    elif update.message.text == '➡':
        if customer.number + 2 >= len(customer.products_from_category):
            await _show_product_sql(customer)
        customer.number = min(customer.number + 1, customer.number_of_products - 1)
    elif update.message.text == '⬅':
        customer.number = max(customer.number - 1, 0)

    reply_keyboard = await _show_product_keyboard(customer)

    number = customer.number
    if customer.products_from_category is None or number >= len(customer.products_from_category):
        logger.exception("%s customer.products_from_category is None %s, %s", user.first_name, number,
                         customer.products_from_category)
        return SELECTION
    image_link, price, product_id, product_link, product_name = await _info_product_from_category(customer, number)
    logger.info("%s рассматривает %s c id %s", user.first_name, product_name, product_id)
    product_name = _to_markdown_v2(product_name)
    caption = f"{product_name}\n" \
              f"Цена: {price} Тенге\n" \
              f"[Ссылка на товар]({product_link})"
    await update.message.reply_photo(
        image_link,
        caption=caption,
        parse_mode='MarkdownV2',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True),
    )
    return SELECTION


def _to_markdown_v2(text):
    return text.replace("-", "\-").replace(".", "\.").replace('!', '\!')


async def _show_product_sql(customer):
    await _db_check_with_logging(customer)
    with customer.connection.connection.cursor() as cur:
        select_products_query = """
        SELECT product_link, image_link, product_name, price, product_id
        FROM product_full_info
        WHERE shop_name = %s AND section_name = %s AND category_name = %s AND availability = true
        ORDER BY product_id DESC
        LIMIT 10
        OFFSET %s"""
        cur.execute(select_products_query,
                    (customer.shop, customer.section, customer.category, len(customer.products_from_category)))
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
        customer.number_of_products = len(customer.products_from_category)


async def _show_product_keyboard(customer):
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
                reply_keyboard[1] = ['🔻', f"{customer.cart[i]['quantity']}", '🔺']
    if customer.cart:
        reply_keyboard[-1].insert(0, 'Корзина')
    return reply_keyboard


async def show_product_after_query(update, context):
    user = update.callback_query.from_user
    customer = context.user_data[user.id]
    reply_keyboard = await _show_product_keyboard(customer)
    number = customer.number
    if customer.products_from_category is None or number >= len(customer.products_from_category):
        logger.exception("%s customer.products_from_category is None", user.first_name)
        return SELECTION
    image_link, price, product_id, product_link, product_name = await _info_product_from_category(customer, number)

    logger.info("%s Вышел из корзины и рассматривает %s c id %s", user.first_name, product_name, product_id)

    product_name = _to_markdown_v2(product_name)
    caption = f"{product_name}\n" \
              f"Цена: {price} Тенге\n" \
              f"[Ссылка на товар]({product_link})"

    await update.callback_query.message.reply_photo(
        image_link,
        caption=caption,
        parse_mode='MarkdownV2',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True),
    )
    return SELECTION


async def _info_product_from_category(customer, number):
    image_link = customer.products_from_category[number]['image_link']
    product_name = customer.products_from_category[number]['product_name'].capitalize()
    price = customer.products_from_category[number]['price']
    product_link = customer.products_from_category[number]['product_link']
    product_id = customer.products_from_category[number]['product_id']
    product_name = product_name.capitalize()
    return image_link, price, product_id, product_link, product_name


async def add_product(update, context):
    user = update.message.from_user
    customer = context.user_data[user.id]
    number = customer.number
    product_id = customer.products_from_category[number]['product_id']
    product_name = customer.products_from_category[number]['product_name']
    price = customer.products_from_category[number]['price']
    product_link = customer.products_from_category[number]['product_link']
    image_link = customer.products_from_category[number]['image_link']

    if customer.cart is None:
        customer.cart = []

    for i, product in enumerate(customer.cart):
        if product['product_id'] == product_id:
            if update.message.text == '🔻':
                customer.cart[i]['quantity'] -= 1
                if customer.cart[i]['quantity'] <= 0:
                    customer.cart.pop(i)
            else:
                customer.cart[i]['quantity'] += 1
            break
    else:
        customer.cart.append({
            'product_id': product_id,
            'name': product_name,
            'quantity': 1,
            'link': product_link,
            'image_link': image_link,
            'price': price})
    if update.message.text != '🔻':
        logger.info("%s добавил в корзину %s c id %s", user.first_name, product_name, product_id)
        message = f'Вы добавили {product_name} в корзину'
    else:
        logger.info("%s убрал из корзины %s c id %s", user.first_name, product_name, product_id)
        message = f'Вы убрали {product_name} из корзины'
    reply_keyboard = await _show_product_keyboard(customer)
    await update.message.reply_text(
        text=message,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    )


async def address(update, context):
    user = update.callback_query.from_user
    customer = context.user_data[user.id]
    logger.info("%s начал оформлять заказ. Корзина: %s", customer.first_name, customer.cart)
    reply_markup = ReplyKeyboardRemove()
    if customer.address:
        reply_markup = ReplyKeyboardMarkup([[customer.address]], resize_keyboard=True)
    await update.callback_query.message.reply_text(
        'Напишите адрес доставки',
        reply_markup=reply_markup
    )
    return ADDRESS


async def shipper(update, context):
    user = update.message.from_user
    context.user_data[user.id].address = update.message.text
    customer = context.user_data[user.id]
    logger.info("%s продолжил оформлять заказ. Корзина: %s", customer.first_name, customer.cart)
    reply_keyboard = [['СДЭК', 'Почта России']]
    await update.message.reply_text(
        'Выберите фирму доставки',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
    return CHECKOUT


async def show_cart_message(update, context):
    user = update.message.from_user
    context.user_data[user.id].cart_position = 0
    customer = context.user_data[user.id]
    await update.message.reply_text('Ваша корзина:', reply_markup=ReplyKeyboardRemove())
    logger.info("%s смотрит корзину. Корзина: %s", customer.first_name, customer.cart)
    reply_keyboard = await _show_cart_keyboard(customer)
    product = customer.cart[customer.cart_position]
    cart_messages = (
        f'{product["name"].capitalize()} \nЦена: {product["price"]}\n')
    await update.message.reply_photo(context.user_data[user.id].cart[0]["image_link"],
                                     caption=cart_messages, reply_markup=InlineKeyboardMarkup(reply_keyboard))
    return CART


async def show_cart_query(update, context):
    user = update.callback_query.from_user
    customer = context.user_data[user.id]
    query = update.callback_query.data
    if query == 'Cart>':
        customer.cart_position = min(customer.cart_position + 1, len(customer.cart) - 1)
    elif query == 'Cart<':
        customer.cart_position = max(customer.cart_position - 1, 0)
    elif query == 'Num+':
        customer.cart[customer.cart_position]['quantity'] += 1
    elif query == 'Num-':
        customer.cart[customer.cart_position]['quantity'] = \
            max(customer.cart[customer.cart_position]['quantity'] - 1, 0)
        if customer.cart[customer.cart_position]['quantity'] == 0:
            customer.cart.pop(customer.cart_position)
            customer.cart_position = 0
        if len(customer.cart) == 0:
            await update.callback_query.message.reply_text('Корзина пуста, начнем заново? /restart')
            return RESTART
    await _logger_show_cart(customer, query)
    reply_keyboard = await _show_cart_keyboard(customer)
    product = context.user_data[user.id].cart[customer.cart_position]
    cart_messages = (
        f'{product["name"].capitalize()} \nЦена: {product["price"]}\n'
    )
    await update.callback_query.edit_message_media(
        InputMediaPhoto(context.user_data[user.id].cart[customer.cart_position]["image_link"]),
        reply_markup=InlineKeyboardMarkup(reply_keyboard))

    await update.callback_query.edit_message_caption(
        caption=cart_messages,
        reply_markup=InlineKeyboardMarkup(reply_keyboard))

    return CART


async def _logger_show_cart(customer, query):
    if query in ('Cart<', 'Cart>'):
        logger.info("%s перелистыват корзину. Корзина: %s", customer.first_name, customer.cart)
    elif query in ('Num-', 'Num+'):
        logger.info("%s изменил количество товара в корзине. Корзина: %s", customer.first_name, customer.cart)
    else:
        logger.info("%s что-то делает в корзине. Корзина: %s", customer.first_name, customer.cart)


async def _show_cart_keyboard(customer):
    reply_keyboard = [
        [
            InlineKeyboardButton("🔻", callback_data='Num-'),
            InlineKeyboardButton(customer.cart[customer.cart_position]['quantity'], callback_data='Nothing'),
            InlineKeyboardButton("🔺", callback_data='Num+')
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
    customer = context.user_data[user.id]
    customer.shipper = update.message.text
    cart_messages = []
    total_price = 0
    for product in customer.cart:
        total_price += product["price"] * product["quantity"]
        product_name = _to_markdown_v2(product["name"])
        cart_messages.append(
            f'{product_name}\n'
            f'Цена: {product["price"]} Тенге\n'
            f'Количество: {product["quantity"]}\n'
            f'[Ссылка на товар]({product["link"]})')
    cart_messages = '\n\n'.join(cart_messages)
    message = f"{_to_markdown_v2('Ваш заказ оформлен!')}" \
              f"\nОбщая стоимость: {total_price} Тенге\n\n" \
              f"{cart_messages}"

    await _db_check_with_logging(customer)
    with customer.connection.connection.cursor() as cur:
        select_user_query = """SELECT customer_id FROM customer"""
        cur.execute(select_user_query)
        users = [user[0] for user in cur.fetchall()]
        if customer.id not in users:
            insert_user_query = """
            INSERT INTO customer (customer_id, first_name, last_name, username)
            VALUES (%s, %s, %s, %s)
            """
            cur.execute(insert_user_query, (user.id, user.first_name, user.last_name, user.username,))

        insert_order_query = """
        INSERT INTO orders (customer_id, order_time, ship_adress, status_id, shipper_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING order_id
        """
        date_time_now = datetime.now(timezone.utc)

        shipper_id = 1
        if customer.shipper == 'Почта России':
            shipper_id = 2
        cur.execute(insert_order_query, (customer.id, date_time_now, customer.address, 1, shipper_id,))
        order_id = cur.fetchone()[0]
        order_detail = []
        for product in customer.cart:
            order_detail.append((product['product_id'], order_id, product["quantity"]))
        insert_order_detail_query = """
        INSERT INTO order_detail (product_id, order_id, quantity)
        VALUES (%s, %s, %s)"""
        psycopg2.extras.execute_batch(cur, insert_order_detail_query, order_detail)
        logger.info("%s оформил заказ. Корзина: %s", customer.first_name, customer.cart)
        context.user_data[user.id].cart = None
        await update.message.reply_markdown_v2(
            text=message,
            reply_markup=ReplyKeyboardMarkup([['Выбрать заново']], resize_keyboard=True))

    return SELECTION


async def error_handler(update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    # tb_string = "".join(tb_list)
    #
    # update_str = update.to_dict() if isinstance(update, Update) else str(update)
    # message = (
    #     f"An exception was raised while handling an update\n"
    #     f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
    #     "</pre>\n\n"
    #     f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
    #     f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
    #     f"<pre>{html.escape(tb_string)}</pre>"
    # )
    # logger.error(msg=message)
    # await context.bot.send_message(chat_id=106683136, text=message, parse_mode="HTML")


if __name__ == '__main__':
    # my_persistence = PicklePersistence(filepath='my_file.pkl')
    # my_persistence = DictPersistence()
    # application = ApplicationBuilder().token(key).persistence(my_persistence).build()
    print(os.getenv('TG_TOKEN_MAG'))
    application = ApplicationBuilder().token(os.getenv('TG_TOKEN_MAG')).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT, start)
        ],
        states={
            RESTART: [CommandHandler('restart', restart)],
            SHOP: [
                MessageHandler(filters.Regex("^(Zara|Next)$"), section_name),
                MessageHandler(filters.Regex("^От тети Глаши$"), fake_shop)],
            SECTION: [
                MessageHandler(filters.Regex(
                    "^(Мужчины|Женщины|Девочки|Мальчики|Малыши|Для дома)"), category_name)],
            CATEGORY: [MessageHandler(filters.TEXT, show_product)],
            SELECTION: [MessageHandler(filters.Regex("^Оформить заказ$"), address),
                        MessageHandler(filters.Regex("^Корзина$"), show_cart_message),
                        MessageHandler(filters.Regex("^(Добавить|🔻|🔺)"), add_product),
                        MessageHandler(filters.Regex("^(➡|⬅|Закрыть корзину)$"), show_product),
                        MessageHandler(filters.Regex("^(Выбрать заново|)$"), restart),
                        MessageHandler(filters.Regex('/^([^0-9]*)$/'), show_product)],
            CART: [CallbackQueryHandler(show_cart_query, pattern="^(Num|Nothing|Cart)"),
                   CallbackQueryHandler(show_product_after_query, pattern="^Menu$"),
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

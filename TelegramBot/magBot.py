import logging
import time
import asyncio
import psycopg2
import random
from key import key
from collections import defaultdict
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

SHOP, SECTION, DATABASE, SELECTION, CATEGORY, RESTART = range(6)

USERS = {}
START_STATE = {
    'shop': None,
    'section': None,
    'category': None,
    'number': 1,
    'cart': None
}


async def start(update, context):
    USERS[update.effective_user.id] = START_STATE
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
    reply_keyboard = [["Мужчины", "Женщины"], ["Мальчики", "Девочки", "Малыши"]]
    if update.message.text == "Next":
        reply_keyboard[1].append("Для дома")
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


async def category_name(update, context):
    user = update.message.from_user
    USERS[user.id]['section'] = update.message.text
    logger.info("%s выбрал секцию: %s", user.first_name, USERS[user.id]['section'])
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
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
        USERS[user.id]['category'] = update.message.text.upper()
        USERS[user.id]['number'] = 1
    else:
        USERS[user.id]['number'] += 1
    logger.info("%s начал искать: %s", user.first_name, USERS[user.id]['category'])
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            store_name = USERS[user.id]['shop']
            section_name = USERS[user.id]['section']
            category_name = USERS[user.id]['category']
            # count_query = """SELECT COUNT(*)
            #                 FROM product_full_info
            #                 WHERE shop_name = %s AND section_name = %s AND category_name = %s"""
            # cur.execute(count_query, (store_name, section_name, category_name))
            # number_of_products = cur.fetchone()[0]
            # print(number_of_products)
            # if not number_of_products:
            #     return SELECTION
            # rand_product = random.randint(1, number_of_products)
            select_query = """SELECT product_link, image_link, product_name, price
                            FROM product_full_info
                            WHERE shop_name = %s AND section_name = %s AND category_name = %s
                            ORDER BY product_id
                            LIMIT 1 OFFSET %s"""
            cur.execute(select_query, (store_name, section_name, category_name, USERS[user.id]['number']))
            records = cur.fetchone()
            product_link = records[0]
            image_link = records[1]
            product_name = records[2]
            price = records[3]
            reply_keyboard = [["Показать еще", 'Выбрать заново', 'Добавить в корзину']]
            if USERS[user.id]['cart']:
                reply_keyboard.append(['Оформить заказ'])
            logger.info("%s: %s, %s", user.first_name, USERS[user.id], product_name)
            # text = f"<a href='{image_link}'>картинка</a>"
            await update.message.reply_markdown_v2(
                text=f"[l]({image_link}) [{product_name.replace('-', ' ').replace('.', ' ')} {price} тг]({product_link})",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                 resize_keyboard=True),
            )
            return SELECTION


async def add_product(update, context):
    user = update.message.from_user
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            store_name = USERS[user.id]['shop']
            section_name = USERS[user.id]['section']
            category_name = USERS[user.id]['category']
            select_query = """SELECT product_name, product_id, product_link, price
                                        FROM product_full_info
                                        WHERE shop_name = %s AND section_name = %s AND category_name = %s
                                        ORDER BY product_id
                                        LIMIT 1 OFFSET %s"""
            cur.execute(select_query, (store_name, section_name, category_name, USERS[user.id]['number']))
            product_name, product_id, product_link, price = cur.fetchone()
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

    reply_keyboard = [["Показать еще", 'Выбрать заново', 'Добавить в корзину'], ['Оформить заказ']]
    await update.message.reply_text(f'Вы добавили {product_name} в корзину',
                                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))


async def checkout(update, context):
    user = update.message.from_user
    logger.info("%s оформил заказ. Корзина: %s", user.first_name, USERS[user.id]['cart'])
    cart_ar = []
    for product in USERS[user.id]['cart']:
        product = USERS[user.id]['cart'][product]
        cart_ar.append(f'Товар: {product["name"]} Цена: {product["price"]} Количество: {product["quantity"]} \n'
                       f'Ссылка : {product["link"]}')
    cart = '\n'.join(cart_ar)
    USERS[user.id]['cart'] = None
    await update.message.reply_text(f'Ваш заказ оформлен! \n'
                                    f'{cart}', reply_markup=ReplyKeyboardRemove())
    return RESTART


if __name__ == '__main__':
    application = ApplicationBuilder().token(key).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SHOP: [MessageHandler(filters.Regex("^(Zara|Next)$"), shop_name),
                   MessageHandler(filters.Regex("^(От тети Глаши)$"), you_stupid)],
            SECTION: [
                MessageHandler(filters.Regex("^(Мужчины|Женщины|Девочки|Мальчики|Малыши|Для дома)$"), category_name)],
            CATEGORY: [MessageHandler(filters.TEXT, random_product)],
            SELECTION: [MessageHandler(filters.Regex("^(Оформить заказ)$"), checkout),
                        MessageHandler(filters.Regex("^(Добавить в корзину)$"), add_product),
                        MessageHandler(filters.Regex("^(Показать еще)$"), random_product),
                        MessageHandler(filters.Regex("^(Выбрать заново|)$"), restart)],
            RESTART: [MessageHandler(filters.TEXT, restart)]
            # DATABASE: [MessageHandler(, random_product)]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    application.add_handler(conv_handler)

    # help_handler = CommandHandler('help', helper)
    # woman_dress_handler = CommandHandler('dress', woman_dress)
    # random_product_handler = CommandHandler('random', random_product)
    # application.add_handler(woman_dress_handler)
    # application.add_handler(help_handler)
    # application.add_handler(random_product_handler)

    # application.add_handler(MessageHandler(filters.TEXT, zara_link))

    application.run_polling()

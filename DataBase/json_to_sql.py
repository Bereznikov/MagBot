import sys

import psycopg2
from db_password import password_railway
import os
import json

def make_sql_categories():
    zara_categories_file = os.path.normpath('../Parsing/zara_categories.json')
    with open(zara_categories_file, 'r') as file:
        zara_categories = json.load(file)
    conn = psycopg2.connect(f"dbname='railway' user='postgres' "
                            f"port=5522 host='containers-us-west-91.railway.app' password={password_railway}")
    print(conn)
    cur = conn.cursor()
    insert_query = """ INSERT INTO category VALUES (%s,%s,%s)"""
    for category in zara_categories:
        category_name = category['category']
        subcategory = category['subcategory']
        id = category['id']
        if category_name == 'ЖЕНЩИНЫ':
            cur.execute(insert_query, (id, subcategory, 1))
        elif category_name == 'МУЖЧИНЫ':
            cur.execute(insert_query, (id, subcategory, 2))
        elif category_name == 'МАЛЫШИ ДЕВОЧКИ' or category_name == 'МАЛЫШИ МАЛЬЧИКИ':
            cur.execute(insert_query, (id, subcategory, 3))
        elif category_name == 'ДЕВОЧКИ':
            cur.execute(insert_query, (id, subcategory, 4))
        elif category_name == 'МАЛЬЧИКИ':
            cur.execute(insert_query, (id, subcategory, 5))
        else:
            print(category_name)
    conn.commit()
    cur.close()
    conn.close()

def insert_into_product_zara():
    zara_categories_file = os.path.normpath('../Parsing/zara_products.json')
    with open(zara_categories_file, 'r') as file:
        zara_products = json.load(file)
    conn = psycopg2.connect(f"dbname='railway' user='postgres' "
                            f"port=5522 host='containers-us-west-91.railway.app' password={password_railway}")
    print(conn)
    cur = conn.cursor()
    insert_query = """ INSERT INTO product VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    for i, product in enumerate(zara_products):
        if i % 10 == 9:
            print(f'[+] Добавил {i + 1} продукт')
            conn.commit()
        id = product['id']
        name = product['name']
        price = product['price']
        price_high = None
        link = product['link']
        image = product['image_path']
        category = product['category_id']
        shop_id = 1
        description = product['description']
        availability = product['availability'] == 'in_stock'
        cur.execute(insert_query, (id, name, price, price_high, link, image, category, shop_id, description, availability))

insert_into_product_zara()





# select_query = """SELECT * FROM shop WHERE shop_id % 13 = 0"""
# cur.execute(select_query)
# records = cur.fetchall()
# print(records)
# for i in range(1000, 1100):
#     cur.execute(insert_query, (i, 'a' * (i % 10)))
# conn.commit()
# print(i)
# cur.close()
# conn.close()
# print(i)
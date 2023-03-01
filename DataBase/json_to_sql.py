import psycopg2
import psycopg2.extras
import os
import json
from db_password import password_railway, host
from time import time


def time_it(func):
    def time_it_wrapper(*args, **kwargs):
        start = int(time())
        result = func(*args, **kwargs)
        total = int(time()) - start
        print(f"Done in {total} s")
        return result

    return time_it_wrapper


def make_sql_categories():
    zara_categories_file = os.path.normpath('../Parsing/zara_categories.json')
    with open(zara_categories_file, 'r') as file:
        zara_categories = json.load(file)
    zara_categories_list = []
    for category in zara_categories:
        category_name = category['category']
        subcategory = category['subcategory']
        id = category['id']
        if category_name == 'ЖЕНЩИНЫ':
            section_id = 1
        elif category_name == 'МУЖЧИНЫ':
            section_id = 2
        elif category_name == 'МАЛЫШИ ДЕВОЧКИ' or category_name == 'МАЛЫШИ МАЛЬЧИКИ':
            section_id = 3
        elif category_name == 'ДЕВОЧКИ':
            section_id = 4
        elif category_name == 'МАЛЬЧИКИ':
            section_id = 5
        else:
            section_id = 123
        _tmp_tuple = (id, subcategory, section_id)
        zara_categories_list.append(_tmp_tuple)
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            insert_query = """ INSERT INTO category VALUES (%s,%s,%s)"""
            psycopg2.extras.execute_batch(cur, insert_query, zara_categories_list)


def insert_into_product_zara():
    zara_products_file = os.path.normpath('../Parsing/zara_products.json')
    with open(zara_products_file, 'r') as file:
        zara_products = json.load(file)
    zara_products_list = []
    for product in zara_products:
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
        _tmp_tuple = (id, name, price, price_high, link, image, category, shop_id, description, availability)
        zara_products_list.append(_tmp_tuple)

    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            insert_query = """ INSERT INTO product VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
            psycopg2.extras.execute_batch(cur, insert_query, zara_products_list)


@time_it
def main():
    make_sql_categories()
    print('Inserted categories')
    insert_into_product_zara()
    print('Inserted products')


if __name__ == '__main__':
    main()
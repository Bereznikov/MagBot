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


def make_sql_categories_all(*files_list):
    categories_list = []
    categories_id = set()
    for file in files_list:
        make_sql_categories_from_one_shop(file, categories_list, categories_id)
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            insert_query = """ INSERT INTO category VALUES (%s,%s,%s)"""
            psycopg2.extras.execute_batch(cur, insert_query, categories_list)


def make_sql_categories_from_one_shop(file_path, categories_list, categories_id):
    categories_file = os.path.normpath(file_path)
    with open(categories_file, 'r') as file:
        categories = json.load(file)
    categories_list = categories_list
    categories_id = categories_id
    section_name_id = {
        'ЖЕНЩИНЫ': 1,
        'МУЖЧИНЫ': 2,
        'МАЛЫШИ ДЕВОЧКИ': 3,
        'МАЛЫШИ МАЛЬЧИК': 3,
        'ДЛЯ МАЛЫШЕЙ': 3,
        'ДЕВОЧКИ': 4,
        'МАЛЬЧИКИ': 5,
        'ДЛЯ ДОМА': 6
    }
    for category in categories:
        category_name = category['category']
        subcategory = category['subcategory']
        id = category['id']
        section_id = section_name_id.get(category_name) or 123
        _tmp_tuple = (id, subcategory, section_id)
        if id not in categories_id:
            categories_id.add(id)
            categories_list.append(_tmp_tuple)


def insert_into_product(file_name, shop):
    products_file = os.path.normpath(file_name)
    products_list = []
    ids_set = set()
    with open(products_file, 'r') as file:
        products_json = json.load(file)
    for product in products_json:
        id = product.get('id')
        name = product.get('name')
        price = product.get('price_low') or product.get('price')
        price_high = product.get('price_big')
        link = product.get('link')
        image = product.get('image_path')
        category = product.get('category_id')
        shop_id = shop
        description = product.get('description')
        availability = product.get('availability') == 'in_stock'
        _tmp_tuple = (id, name, price, price_high, link, image, category, shop_id, description, availability)
        if id not in ids_set and category:
            ids_set.add(id)
            products_list.append(_tmp_tuple)
        else:
            print(id, category)
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            insert_query = """ INSERT INTO product VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
            psycopg2.extras.execute_batch(cur, insert_query, products_list)


@time_it
def main():
    make_sql_categories_all('../Parsing/zara_categories.json', '../Parsing/next_categories_redacted.json')
    print('Inserted categories')
    insert_into_product('../Parsing/zara_products.json', 1)
    print('Inserted products zara')
    insert_into_product('../Parsing/next_updated.json', 2)
    print('Inserted products next')


if __name__ == '__main__':
    main()

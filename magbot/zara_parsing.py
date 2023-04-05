import asyncio
import time
import aiohttp
import requests
from fake_useragent import UserAgent
from db_connection import PostgresConnection
import json
import psycopg2.extras


def make_headers():
    ua = UserAgent()
    return {'User-Agent': ua.random}


def dump_to_file(data, file_name):
    with open(file_name, "w") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def products_from_db(conn):
    conn.strong_check()
    with conn.connection.cursor() as cur:
        select_query = 'SELECT product_id, category_id, availability FROM product WHERE shop_id=1'
        cur.execute(select_query)
        records = cur.fetchall()
        products = {}
        for rec in records:
            products[rec[0]] = rec[1], rec[2]
        return products


def categories_ids_from_db(conn):
    conn.strong_check()
    with conn.connection.cursor() as cur:
        select_query = 'SELECT category_id FROM category'
        cur.execute(select_query)
        records = cur.fetchall()
        categories = set(rec[0] for rec in records)
        return categories


def _new_categories(zara_categories):
    new_categories_list = []
    for category in zara_categories:
        if category['is_new']:
            section_id = category['section_id']
            category_name = category['subcategory']
            category_id = category['id']
            new_categories_list.append((category_id, category_name, section_id))
    return new_categories_list


def insert_new_categories(conn, categories):
    conn.strong_check()
    with conn.connection.cursor() as cur:
        insert_query = """ INSERT INTO category VALUES (%s,%s,%s)"""
        psycopg2.extras.execute_batch(cur, insert_query, categories)


async def make_categories_links(url, db_categories):
    full_categories_links = requests.get(url=url, headers=make_headers()).json()
    zara_categories_full = full_categories_links['categories']
    zara_categories = []
    unique_category_ids = set()

    for category in zara_categories_full:
        if category['name'] != 'ДЕТИ':
            check_all_subcategory(category, zara_categories, category, unique_category_ids, '', db_categories)
    children_category = zara_categories_full[2]['subcategories']
    for category in children_category:
        check_all_subcategory(category, zara_categories, category, unique_category_ids, '', db_categories)
    return await clean_categories_links(zara_categories)


async def get_html(url, category, clean_categories):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=make_headers()) as resp:
            text = await resp.text()
            if text != '{"productGroups":[]}' and len(text) > 600:
                clean_categories.append(category)


async def clean_categories_links(zara_categories):
    tasks = []
    clean_categories = []
    for category in zara_categories:
        task = asyncio.create_task(get_html(category['url'], category, clean_categories))
        tasks.append(task)
    await asyncio.gather(*tasks)
    print(f"Почистил ссылки, было {len(zara_categories)}, стало {len(clean_categories)}")
    return clean_categories


def add_to_categories_list(category, subcategory, zara_categories, unique_category_ids, category_name, db_categories):
    try:
        section_name = subcategory['sectionName']
    except KeyError:
        return
    sub_category_ap = str(subcategory['id'])
    if sub_category_ap not in unique_category_ids:
        subcategory_url = f'https://www.zara.com/kz/ru/category/{subcategory["id"]}/products?ajax=true'
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
        category_name_ap = category['name'].replace(' ', ' ')
        section_id = section_name_id.get(category_name_ap) or 123
        zara_categories.append({
            'category': category_name_ap,
            'subcategory': category_name.strip().upper(),
            'id': sub_category_ap,
            'url': subcategory_url,
            'section_name': section_name,
            'section_id': section_id,
            'is_new': sub_category_ap not in db_categories
        })
        unique_category_ids.add(sub_category_ap)


def check_all_subcategory(category, zara_categories, original, unique_ids, category_name, db_categories):
    for subcategory in category['subcategories']:
        tmp_subcategory = subcategory['name'].replace(' ', ' ')
        add_to_categories_list(original, subcategory, zara_categories, unique_ids, f'{category_name} {tmp_subcategory}',
                               db_categories)
        check_all_subcategory(subcategory, zara_categories, original, unique_ids, f'{category_name} {tmp_subcategory}',
                              db_categories)


async def get_product(zara_categories, db_products_ids):
    tasks = []
    new_products_zara = []
    update_category_products = []
    unique_product_ids = {}
    availability_false_product_ids = set()
    availability_true_product_ids = set()
    for category in zara_categories:
        id = category['id']
        url = category['url']
        task = asyncio.create_task(
            get_product_from_category(new_products_zara, update_category_products, db_products_ids, url, id,
                                      unique_product_ids))
        tasks.append(task)
    await asyncio.gather(*tasks)
    print(f'Обработал все категории')
    for product in db_products_ids:
        if (product not in unique_product_ids) and db_products_ids[product][1]:
            availability_false_product_ids.add(product)
        if product in unique_product_ids and unique_product_ids[product][1] and not db_products_ids[product][1]:
            availability_true_product_ids.add(product)

    return new_products_zara, update_category_products, list(availability_false_product_ids), list(
        availability_true_product_ids)


async def get_product_from_category(new_products_zara, update_product_categories, db_products_ids, url, id,
                                    unique_product_ids):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=make_headers()) as resp:
            category_info = await resp.json()
    elements = category_info['productGroups'][0]['elements']
    for el_num, elem in enumerate(elements):
        try:
            commercialComponents = elem['commercialComponents']
        except KeyError:
            continue
        except Exception as ex:
            print('WTF IS HAPPENING?!', ex, ex.__class__)
            continue
        for comp in commercialComponents:
            if comp['type'] != 'Bundle':
                try:
                    image_comp = comp['xmedia'][0]
                    image_path = f'https://static.zara.net/photos{image_comp["path"]}/w/750/{image_comp["name"]}' \
                                 f'.jpg?ts={image_comp["timestamp"]}'
                except IndexError:
                    image_path = None
                try:
                    seo = comp['seo']
                    link_path = f'https://www.zara.com/kz/ru/{seo["keyword"]}-p{seo["seoProductId"]}' \
                                f'.html?v1={seo["discernProductId"]}'
                except IndexError:
                    link_path = None
                product_id = str(comp['id'])

                if product_id in unique_product_ids:
                    continue
                availability = comp.get('availability') == 'in_stock'
                unique_product_ids[product_id] = id, availability

                if product_id in db_products_ids and db_products_ids[product_id][0] != id:
                    update_product_categories.append((id, product_id, availability))
                    continue
                if product_id in db_products_ids:
                    continue
                new_products_zara.append({
                    'product_id': product_id,
                    'product_name': comp.get('name'),
                    'price': comp.get('price') // 100,
                    'product_link': link_path,
                    'image_link': image_path,
                    'availability': availability,
                    'description': comp.get('description'),
                    'category_id': id,
                })
                unique_product_ids[product_id] = id


def insert_into_product(conn, new_products_zara):
    products_list = []
    for product in new_products_zara:
        id = product.get('product_id')
        name = product.get('product_name')
        price = product.get('price')
        price_high = None
        link = product.get('product_link')
        image = product.get('image_link')
        category = product.get('category_id')
        shop_id = 1
        description = product.get('description')
        availability = product.get('availability')
        _tmp_tuple = (id, name, price, price_high, link, image, category, shop_id, description, availability)
        products_list.append(_tmp_tuple)
    conn.strong_check()
    with conn.connection.cursor() as cur:
        insert_query = """ INSERT INTO product VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        psycopg2.extras.execute_batch(cur, insert_query, products_list)


def update_product_availability_set_false(conn, availability_false_product_ids):
    availability_false_product_ids = [(a,) for a in availability_false_product_ids]
    conn.strong_check()
    with conn.connection.cursor() as cur:
        update_query = """
        UPDATE product SET availability=false
        FROM (VALUES %s) AS update_payload (id)
        WHERE product_id=update_payload.id"""
        psycopg2.extras.execute_values(cur, update_query, availability_false_product_ids)


def update_product_availability_set_true(conn, availability_true_product_ids):
    availability_true_product_ids = [(a,) for a in availability_true_product_ids]
    conn.strong_check()
    with conn.connection.cursor() as cur:
        update_query = """
                UPDATE product SET availability=true
                FROM (VALUES %s) AS update_payload (id)
                WHERE product_id=update_payload.id"""
        psycopg2.extras.execute_values(cur, update_query, availability_true_product_ids)


async def one_run():
    pg_con = PostgresConnection()
    db_products_ids = products_from_db(pg_con)
    db_categories = categories_ids_from_db(pg_con)
    print('Собрал данные с Базы данных')

    zara_categories = await make_categories_links(
        'https://www.zara.com/kz/ru/categories?categoryId=21872718&ajax=true', db_categories)
    new_categories_list = _new_categories(zara_categories)
    insert_new_categories(pg_con, new_categories_list)
    print('Заинсертил новые категории', len(new_categories_list))
    await asyncio.sleep(60)
    new_products_zara, update_category_products, availability_false_product_ids, availability_true_product_ids = \
        await get_product(zara_categories, db_products_ids)
    print(len(new_products_zara), len(availability_false_product_ids), len(availability_true_product_ids))

    insert_into_product(pg_con, new_products_zara)
    print('Заинсертил новые товары', len(new_products_zara))

    update_product_availability_set_false(pg_con, availability_false_product_ids)
    print("Заапдейтил наличие, поставил значение False", len(availability_false_product_ids))

    update_product_availability_set_true(pg_con, availability_true_product_ids)
    print("Заапдейтил наличие, поставил значение True", len(availability_true_product_ids))


async def main():
    run_number = 0
    while True:
        run_number += 1
        print(f'[+] Пошли на run с номером {run_number}')
        try:
            start_time = time.time()
            await one_run()
            run_time = time.time() - start_time
            print(f'Отработал run за {run_time}')
            await asyncio.sleep(3600 - run_time)
        except Exception as ex:
            print(ex.__class__)
            await asyncio.sleep(36060)


if __name__ == '__main__':
    asyncio.run(main())

import requests
from fake_useragent import UserAgent
from TelegramBot.db_connection import PostgresConnection
import json
import psycopg2.extras


# import json


def make_headers():
    ua = UserAgent()
    return {'User-Agent': ua.random}


def dump_to_file(data, file_name):
    with open(file_name, "w") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def product_ids_in_db(conn):
    with conn.connection.cursor() as cur:
        select_query = 'SELECT product_id, category_id FROM product WHERE shop_id=1'
        cur.execute(select_query)
        records = cur.fetchall()
        products_ids = {}
        for rec in records:
            products_ids[rec[0]] = rec[1]
        return products_ids


def categories_ids_in_db(conn):
    with conn.connection.cursor() as cur:
        select_query = 'SELECT category_id FROM category'
        cur.execute(select_query)
        records = cur.fetchall()
        categories_ids = set(rec[0] for rec in records)
        return categories_ids


def new_categories(zara_categories):
    new_categories_list = []
    for category in zara_categories:
        if category['is_new']:
            section_id = category['section_id']
            category_name = category['subcategory']
            category_id = category['id']
            new_categories_list.append((category_id, category_name, section_id))
    return new_categories_list


def insert_categories(conn, categories):
    conn.strong_check()
    with conn.connection.cursor() as cur:
        insert_query = """ INSERT INTO category VALUES (%s,%s,%s)"""
        psycopg2.extras.execute_batch(cur, insert_query, categories)


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


def clean_categories_links(zara_categories):
    clean_categories = []
    for i, category in enumerate(zara_categories):
        print(f'[+] ЧИЩУ ЛИНКИ {i + 1}/{len(zara_categories)} {category["url"]}')
        r = requests.get(category['url'], headers=make_headers())
        if r.text == '{"productGroups":[]}':
            continue
        else:
            clean_categories.append(category)
    return clean_categories


def check_all_subcategory(category, zara_categories, original, unique_ids, category_name, db_categories):
    for subcategory in category['subcategories']:
        tmp_subcategory = subcategory['name'].replace(' ', ' ')
        add_to_categories_list(original, subcategory, zara_categories, unique_ids, f'{category_name} {tmp_subcategory}',
                               db_categories)
        check_all_subcategory(subcategory, zara_categories, original, unique_ids, f'{category_name} {tmp_subcategory}',
                              db_categories)


def make_categories_links(url, db_categories):
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
    # print('Сделал плосские категории')
    return clean_categories_links(zara_categories)


def get_product(zara_categories, db_products_ids):
    new_products_zara = []
    update_category_products = []
    unique_product_ids = {}
    for i, category in enumerate(zara_categories):
        print(f'[+] Обработка {i + 1}/{len(zara_categories)} {category["subcategory"]} {category["id"]}')
        id = category['id']
        url = category['url']
        get_product_from_category(new_products_zara, update_category_products, db_products_ids, url, id,
                                  unique_product_ids)

    return new_products_zara, update_category_products


def get_product_from_category(new_products_zara, update_product_categories, db_products_ids, url, id,
                              unique_product_ids):
    category_info = requests.get(url=url, headers=make_headers()).json()
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
                # if comp.get('id') is None:
                #     print("ЧТО_ТО УЖАСНОЕ, ТАКОГО ТОВАРА НЕТ", comp)
                #     continue
                product_id = str(comp['id'])
                if product_id in unique_product_ids:
                    continue
                unique_product_ids[product_id] = id
                if db_products_ids.get(product_id) and db_products_ids[product_id] != id:
                    print(
                        f'Было product_id {product_id} category_id:{db_products_ids[product_id]}, новая категория {id}')
                    update_product_categories.append((id, product_id))
                    unique_product_ids[product_id] = id
                    continue
                if product_id in db_products_ids:
                    continue
                new_products_zara.append({
                    'product_id': product_id,
                    'product_name': comp.get('name'),
                    'price': comp.get('price') // 100,
                    'product_link': link_path,
                    'image_link': image_path,
                    'availability': comp.get('availability') == 'in_stock',
                    'description': comp.get('description'),
                    'category_id': id,
                })
                unique_product_ids[product_id] = id


def insert_into_product(conn, new_products_zara):
    # with open(products_file, 'r') as file:
    #     new_products_zara = json.load(file)
    conn.strong_check()
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
    with conn.connection.cursor() as cur:
        insert_query = """ INSERT INTO product VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        psycopg2.extras.execute_batch(cur, insert_query, products_list)


def update_product_category(conn, update_category_products):
    # with open(file_name, 'r') as file:
    #     update_category_products = json.load(file)
    pg_con = PostgresConnection()

    with pg_con.connection.cursor() as cur:
        for record in update_category_products:
            cur.execute(""" UPDATE product SET category_id=%s WHERE product_id=%s""", (record[0], record[1],))
            pg_con.connection.commit()
        # cur.execute("PREPARE updateStmt AS UPDATE product SET category_id=$1 WHERE product_id=$2")
        # psycopg2.extras.execute_batch(cur, "EXECUTE updateStmt (%s, %s)", update_category_products)
        # update_query = """ UPDATE product SET category_id=%s WHERE product_id=%s"""
        # psycopg2.extras.execute_values(cur, update_query, update_category_products)


def update_product_availability(conn, update_products_availability):
    conn.strong_check()
    with conn.connection.cursor() as cur:
        update_query = """ UPDATE product SET availability=false WHERE product_id=%s"""
        psycopg2.extras.execute_values(cur, update_query, update_products_availability)


def main():
    pg_con = PostgresConnection()
    db_products_ids = product_ids_in_db(pg_con)
    db_categories = categories_ids_in_db(pg_con)

    zara_categories = make_categories_links('https://www.zara.com/kz/ru/categories?categoryId=21872718&ajax=true',
                                            db_categories)
    new_categories_list = new_categories(zara_categories)
    insert_categories(pg_con, new_categories_list)

    new_products_zara, update_category_products = get_product(zara_categories, db_products_ids)
    # dump_to_file(file_name='zara_products.json', data=new_products_zara)
    # dump_to_file(file_name='zara_products_update_category.json', data=update_category_products)

    insert_into_product(pg_con, new_products_zara)
    print('Заинсертил', len(new_products_zara))

    update_product_category(pg_con, update_category_products)
    print("Заапдейтил", len(update_category_products))


if __name__ == '__main__':
    main()

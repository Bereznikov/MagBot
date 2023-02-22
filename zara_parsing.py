import requests
from fake_useragent import UserAgent
import json
import os


def make_headers():
    ua = UserAgent()
    return {'User-Agent': ua.random}


def dump_to_file(data, file_name):
    with open(file_name, "w") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def make_full_categories_links(url, file_name):
    full_categories = requests.get(url=url, headers=make_headers())
    dump_to_file(data=full_categories.json(), file_name=file_name)


def add_to_categories_list(category, subcategory, zara_categories):
    subcategory_url = f'https://www.zara.com/kz/ru/category/{subcategory["id"]}/products?ajax=true'
    zara_categories.append({
        'category': category['name'].replace(' ', ' '),
        'subcategory': subcategory['name'].replace(' ', ' '),
        'id': subcategory['id'],
        'url': subcategory_url
    })


def clean_categories_links(file_from, file_to):
    with open(file_from, "r") as file:
        zara_categories = json.load(file)
    clean_categories = []
    for i, category in enumerate(zara_categories):
        print(f'[+] ЧИЩУ ЛИНКИ {i + 1}/{len(zara_categories)} {category["url"]}')
        r = requests.get(category['url'], headers=make_headers())
        if r.text == '{"productGroups":[]}':
            continue
        else:
            clean_categories.append(category)
    dump_to_file(clean_categories, file_to)


def check_all_subcategory(category, zara_categories, original):
    for subcategory in category['subcategories']:
        add_to_categories_list(original, subcategory, zara_categories)
        check_all_subcategory(subcategory, zara_categories, original)


def make_categories_links(url):
    make_full_categories_links(url, 'zara_categories_full.json')

    with open("zara_categories_full.json", "r") as file:
        zara_categories_full = json.load(file)['categories']

    zara_categories = []

    for category in zara_categories_full:
        if category['name'] != 'ДЕТИ':
            check_all_subcategory(category, zara_categories, category)

    children_category = zara_categories_full[2]['subcategories']
    for category in children_category:
        check_all_subcategory(category, zara_categories, category)

    dirty_file_name = 'zara_categories.json'
    clean_file_name = 'zara_categories_clean.json'
    dump_to_file(data=zara_categories, file_name=dirty_file_name)

    clean_categories_links(dirty_file_name, clean_file_name)


def get_product(file_name):
    with open(file_name, 'r') as file:
        zara_categories = json.load(file)
    if not os.path.exists('products'):
        os.mkdir('products')

    products_zara = []
    for i, category in enumerate(zara_categories):
        print(f'[+] Обработка {i}/{len(zara_categories)} {category["subcategory"]}')
        id = category['id']
        url = category['url']
        get_product_from_category(products_zara, url, id)
    return products_zara


def get_product_from_category(products_zara, url, id):
    category_info = requests.get(url=url, headers=make_headers()).json()
    dump_to_file(data=category_info, file_name=f'products/category_{id}.json')
    with open(f'products/category_{id}.json', 'r') as file:
        loaded_file = json.load(file)
        elements = loaded_file['productGroups'][0]['elements']
    for el_num, elem in enumerate(elements):
        try:
            commercialComponents = elem['commercialComponents']
        except KeyError:
            continue
        except:
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
                    link_path = f'https://www.zara.com/kz/ru/{seo["keyword"]}-p{seo["seoProductId"]}'\
                                f'.html?v1={seo["discernProductId"]}'
                except IndexError:
                    link_path = None

                products_zara.append({
                    'id': comp.get('id'),
                    'name': comp.get('name'),
                    'price': comp.get('price') // 100,
                    'link': link_path,
                    'image_path': image_path,
                    'availability': comp.get('availability'),
                    'description': comp.get('description'),
                    'section': comp.get('section'),
                    'category_id': id,
                    # 'type': comp['type'],
                    # 'category_url': url[0],
                    # 'el_num': el_num,
                })


def main():
    make_categories_links('https://www.zara.com/kz/ru/categories?categoryId=21872718&ajax=true')
    zara_products = get_product('zara_categories_clean.json')
    dump_to_file(file_name='zara_products.json', data=zara_products)
    print(len(zara_products), "FINISHED")



if __name__ == '__main__':
    main()

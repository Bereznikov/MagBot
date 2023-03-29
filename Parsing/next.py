from fake_useragent import UserAgent
import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import psycopg2
import psycopg2.extras
from db_password import password_railway, host


class Parser:
    def __init__(self):
        self._section_links = []
        self._section_names = ['ДЕВОЧКИ', 'МАЛЬЧИКИ', 'ДЛЯ МАЛЫШЕЙ', 'ЖЕНЩИНЫ', "МУЖЧИНЫ", "ДЛЯ ДОМА"]
        self.result = []
        self.id_set = set()

    @staticmethod
    def making_soup_txt(url):
        ua = UserAgent()
        fake_ua = {'user-agent': ua.random}
        response = requests.get(url=url, headers=fake_ua)
        response.encoding = 'utf-8'
        return BeautifulSoup(response.text, 'lxml')

    @staticmethod
    def get_url_sections(soup):
        res = []
        sections = [f'{link["href"]}' for link in soup.find('ul', id='snail-trail-container').find_all('a')]
        for section in sections:
            res.append(section)
        del res[5]  # отсеиваем секции сайта состоящие из повторений продуктов
        res = res[:-3]  # отсеиваем секции сайта состоящие из повторений продуктов
        return res

    @staticmethod
    def summary_categories_check(link):
        if ('Вся ' in link.text) or ('Все ' in link.text) or ('Новинки' in link.text) or (
                'Новые ' in link.text) or ('Всё ' in link.text):
            return True
        else:
            return False

    def women_check(self, url, soup):
        categories_links = []
        categories_names = []
        for link in soup.find_all('div', class_="sidebar-sec col-sm-12 col-md-3 col-lg-12"):
            women_links = link.find_all('a')
            for women_link in women_links:
                if 'Все Дамское белье' in women_link.text:
                    categories_links.append(f'{url[:33]}{women_link["href"][7:]}')
                    categories_names.append(women_link.text)
                elif self.summary_categories_check(women_link):  # проверка на наличие обобщенных категорий
                    continue
                else:
                    categories_links.append(f'{url[:33]}{women_link["href"][7:]}')
                    categories_names.append(women_link.text)
        categories_links = categories_links[:15] + [categories_links[27]] + categories_links[30:]
        categories_names = categories_names[:15] + [categories_names[27]] + categories_names[30:]
        return zip(categories_names, categories_links)

    def kids_check(self, url, soup):
        categories_links = []
        categories_names = []
        link_list = soup.find_all('div', class_='row tablet-rows')[1]
        for link in link_list.find_all('a'):
            if self.summary_categories_check(link):  # проверка на наличие обобщенных категорий
                continue
            else:
                categories_links.append(f'{url[:33]}{link["href"][7:]}')
                categories_names.append(link.text)
        categories_links = categories_links[-6:]
        categories_names = categories_names[-6:]
        return zip(categories_names, categories_links)

    def normal_chek(self, url, soup):
        categories_links = []
        categories_names = []
        for link in soup.find('div', class_='row tablet-rows').find_all('a'):
            if self.summary_categories_check(link):  # проверка на наличие обобщенных категорий
                continue
            else:
                categories_links.append(f'{url[:33]}{link["href"][7:]}')
                categories_names.append(link.text)
        return zip(categories_names, categories_links)

    def get_url_categories(self, url):
        soup = self.making_soup_txt(url)
        if url == 'https://www.nextdirect.com/kz/ru/women':
            res = self.women_check(url, soup)
        elif url == 'https://www.nextdirect.com/kz/ru/baby':
            res = self.kids_check(url, soup)
        else:
            res = self.normal_chek(url, soup)
        return res

    async def get_data(self, session, info_pair, counter):
        section_name = self._section_names[counter]
        category_name = info_pair[0].strip()
        url = info_pair[1]
        for i in range(1, 826):
            pagen_url = url.strip('-0') + '?p=' + str(i)
            async with session.get(url=pagen_url) as response:
                resp = await response.text()
                page_soup = BeautifulSoup(resp, 'lxml')
                items = page_soup.find('div',
                                       "MuiGrid-root MuiGrid-container plp-product-grid-wrapper plp-1s9f1m4").find_all(
                    'div', class_="MuiCardContent-root produc-1ivfcou")
                if items:
                    for item in items:
                        name_id, price, *tale = item.find('a')['aria-label'].split(' | ')
                        good_name = name_id[:name_id.find(' (')]
                        good_id = name_id.rstrip(')').lstrip(' (')[-6:]
                        good_link = item.find('a')['href']
                        previous_sib = item.previous_sibling
                        image = previous_sib.find('img')['src']
                        if '-' in price or '&' in good_id:
                            try:
                                price_low = price.split(' - ')[0].strip(' тг').replace(' ', '')
                                price_big = price.split(' - ')[1].strip(' тг').replace(' ', '')
                                good_dict = {'id': good_id,
                                             'name': good_name,
                                             'price_low': price_low,
                                             'price_big': price_big,
                                             'link': good_link,
                                             'image_path': image,
                                             'availability': 'in_stock',
                                             'section_name': section_name,
                                             'category_name': category_name}
                            except IndexError:
                                brand, name_id, price, *tale = item.find('a')['aria-label'].split(' | ')
                                good_name = name_id[:name_id.find(' (')]
                                good_id = name_id.rstrip(')').lstrip(' (')[-6:]
                                good_dict = {'id': good_id,
                                             'name': good_name,
                                             'price_low': price.strip('тг').replace(' ', ''),
                                             'price_big': price.strip('тг').replace(' ', ''),
                                             'link': good_link,
                                             'image_path': image,
                                             'availability': 'in_stock',
                                             'section_name': section_name,
                                             'category_name': category_name}
                        else:
                            good_dict = {'id': good_id,
                                         'name': good_name,
                                         'price_low': price.strip('тг').replace(' ', ''),
                                         'price_big': price.strip('тг').replace(' ', ''),
                                         'link': good_link,
                                         'image_path': image,
                                         'availability': 'in_stock',
                                         'section_name': section_name,
                                         'category_name': category_name}
                        if good_dict['id'] not in self.id_set:
                            self.result.append(good_dict)
                            self.id_set.add(good_dict['id'].upper())
                        else:
                            continue
                else:
                    break

    async def main(self):
        counter = 0
        ua = UserAgent()
        fake_ua = {'user-agent': ua.random}
        async with aiohttp.ClientSession(headers=fake_ua) as session:
            tasks = []
            for section_link in self._section_links:
                category_names_links = self.get_url_categories(section_link)
                for category_pair in category_names_links:
                    task = asyncio.create_task(self.get_data(session, category_pair, counter))
                    tasks.append(task)
                counter += 1
            await asyncio.gather(*tasks)

    def make_next_json_with_category_id(self):
        next_product = self.result
        with open('next_categories_redacted.json', 'r', encoding='utf-8') as file:
            next_categories = json.load(file)
        next_categories_dict = {}
        for category in next_categories:
            next_categories_dict[category['category'] + category['subcategory']] = category['id']
        for product in next_product:
            if next_categories_dict.get(product['section_name'].upper() + product['category_name'].upper()):
                product['category_id'] = next_categories_dict.get(
                    product['section_name'].upper() + product['category_name'].upper())
        with open('next_updated.json', "w", encoding='utf-8') as file:
            json.dump(next_product, file, indent=4, ensure_ascii=False)

    def __call__(self, url, *args, **kwargs):
        soup = self.making_soup_txt(url)
        sections = self.get_url_sections(soup)
        self._section_links = sections
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(self.main())
        self.make_next_json_with_category_id()


def find_new_ids(obj):
    set_id = obj.id_set
    new_ids = []
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""SELECT product_id FROM product WHERE shop_id = 2""")
            query_result = cur.fetchall()
            for i in set_id:
                if i not in map(lambda x: x[0], query_result):
                    new_ids.append(i)
    return new_ids


def update_items(obj):
    counter = 0
    set_id = obj.id_set
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""SELECT product_id FROM product WHERE shop_id = 2 AND availability = true""")
            query_result = cur.fetchall()
            for item_id in query_result:
                if item_id[0] not in set_id:
                    cur.execute(f"UPDATE product SET availability = false WHERE product_id = '{item_id[0]}'")
                    counter += 1
                    print(item_id[0], end=':')
            cur.execute("""SELECT product_id FROM product WHERE shop_id = 2 AND availability = false""")
            query_result = cur.fetchall()
            for item_id in query_result:
                if item_id[0] in set_id:
                    cur.execute(f"UPDATE product SET availability = true WHERE product_id = '{item_id[0]}'")
                    counter += 1
                    print(item_id[0], end=';')
    print()
    print('Обновлен статус продуктов:', counter)


def insert_new_products(new_ids):
    with open('next_updated.json', "r", encoding='utf-8') as file:
        products = json.load(file)
    products_list = []
    new_products = []
    for i in new_ids:
        for product in products:
            if product['id'] == i:
                new_products.append(product)
    ids_set = set()
    for product in new_products:
        product_id = product.get('id')
        name = product.get('name')
        price = product.get('price_low') or product.get('price')
        price_high = product.get('price_big')
        link = product.get('link')
        image = product.get('image_path')
        category = product.get('category_id')
        shop_id = 2
        description = product.get('description')
        availability = product.get('availability') == 'in_stock'
        _tmp_tuple = (product_id, name, price, price_high, link, image, category, shop_id, description, availability)
        if product_id not in ids_set and category:
            ids_set.add(product_id)
            products_list.append(_tmp_tuple)
        else:
            print(product_id, category)
    with psycopg2.connect(dbname='railway', user='postgres', port=5522, host=host,
                          password=password_railway) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            insert_query = """ INSERT INTO product VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
            psycopg2.extras.execute_batch(cur, insert_query, products_list)
            print('Добавлено новых продуктов:', len(products_list))


if __name__ == '__main__':
    db_url = 'postgresql://postgres:jisJH7i2ddKod3ItAfj5@containers-us-west-91.railway.app:5522/railway'
    parse_site = Parser()
    parse_site('https://www.nextdirect.com/kz/ru')
    new_items = find_new_ids(parse_site)
    if new_items:
        print('Появились новые вещи')
        print('Количество:', len(new_items))
        print(new_items)
        insert_new_products(new_items)
    update_items(parse_site)

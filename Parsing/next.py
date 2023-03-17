from fake_useragent import UserAgent
import requests
import asyncio
import aiohttp
# from aiohttp_retry import RetryClient, ExponentialRetry
from bs4 import BeautifulSoup
import json


class Parser:
    def __init__(self):
        self._section_links = []
        self._section_names = ['Девочки', 'Мальчики', 'Для малышей', 'Женщины', "Мужчины", "Для дома"]
        self.result = []
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
        result = []
        section_name = self._section_names[counter]
        category_name = info_pair[0]
        url = info_pair[1]
        for i in range(1, 826):
                pagen_url = url.strip('-0') + '?p=' + str(i)
                async with session.get(url=pagen_url) as response:
                    resp = await response.text
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
                                except:
                                    brand, name_id, price, *tale = item.find('a')['aria-label'].split(' | ')
                                    good_name = name_id[:name_id.find(' (')]
                                    good_id = name_id.rstrip(')').lstrip(' (')[-6:]
                                    good_dict = {'id': good_id,
                                                'name': good_name,
                                                'price_low': price.strip('тг').replace(' ', ''),
                                                'price_big': price.strip('тг').replace(' ', ''),
                                                'link': good_link, 'image_path': image,
                                                'availability': 'in_stock',
                                                'section_name': section_name,
                                                'category_name': category_name}
                            else:
                                good_dict = {'id': good_id,
                                            'name': good_name,
                                            'price_low': price.strip('тг').replace(' ', ''),
                                            'price_big': price.strip('тг').replace(' ', ''),
                                            'link': good_link,
                                            'image_path': image, 'availability': 'in_stock',
                                            'section_name': section_name,
                                            'category_name': category_name}
                            result.append(good_dict)
                    else:
                        break
                    with open('next.json', 'a', encoding='utf-8') as file:
                        json.dump(result, file, indent=4, ensure_ascii=False)

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

    def __call__(self, url, *args, **kwargs):
        soup = self.making_soup_txt(url)
        sections = self.get_url_sections(soup)
        self._section_links = sections




if __name__ == '__main__':
    parse_site = Parser()
    parse_site('https://www.nextdirect.com/kz/ru')


# urlmain = 'https://www.nextdirect.com/kz/ru'
# soupmain = makingsouptxt(urlmain)
# primecategories = [f'{link["href"]}' for link in soupmain.find('ul', id='snail-trail-container').find_all('a')]
# primecategories_names = [link.find('div', class_="header-5qe5c1").text for link in
#                          soupmain.find('ul', id='snail-trail-container').find_all('a')]
# primecounter = 0
# del primecategories[5]
# del primecategories_names[5]
# res = []
# id_list = []
# id_set = set()
# for primelink in primecategories[:-3]:
#     url = primelink
#     soup = makingsouptxt(url)
#     primecategory_name = primecategories_names[primecounter]
#     primecounter += 1
#     categories_links = []
#     categories_names = []
#     if primelink == 'https://www.nextdirect.com/kz/ru/women':
#         for link in soup.find_all('div', class_="sidebar-sec col-sm-12 col-md-3 col-lg-12"):
#             women_links = link.find_all('a')
#             for women_link in women_links:
#                 if 'Все Дамское белье' in women_link.text:
#                     categories_links.append(f'{url[:33]}{women_link["href"][7:]}')
#                 elif ('Вся ' in women_link.text) or ('Все ' in women_link.text) or ('Новинки' in women_link.text) or (
#                     'Новые ' in women_link.text) or ('Всё ' in women_link.text):
#                     continue
#                 else:
#                     categories_links.append(f'{url[:33]}{women_link["href"][7:]}')
#             for women_link in women_links:
#                 if 'Все Дамское белье' in women_link.text:
#                     categories_names.append(women_link.text)
#                 elif ('Вся ' in women_link.text) or ('Все ' in women_link.text) or ('Новинки' in women_link.text) or (
#                     'Новые ' in women_link.text) or ('Всё ' in women_link.text):
#                     continue
#                 else:
#                     categories_names.append(women_link.text)
#         counter = 0
#         categories_links = categories_links[:15] + [categories_links[28]] + categories_links[31:]
#         categories_names = categories_names[:15] + [categories_names[28]] + categories_names[31:]
#     elif primelink == 'https://www.nextdirect.com/kz/ru/baby':
#         link_list = soup.find_all('div', class_='row tablet-rows')[1]
#         for link in link_list.find_all('a'):
#             if ('Вся ' in link.text) or ('Все ' in link.text) or ('Новинки' in link.text) or (
#                     'Новые ' in link.text) or ('Всё ' in link.text):
#                 continue
#             else:
#                 categories_links.append(f'{url[:33]}{link["href"][7:]}')
#         for link in link_list.find_all('a'):
#             if ('Вся ' in link.text) or ('Все ' in link.text) or ('Новинки' in link.text) or (
#                     'Новые ' in link.text) or ('Всё ' in link.text):
#                 continue
#             else:
#                 categories_names.append(link.text)
#         counter = 0
#         categories_links = categories_links[-6:]
#         categories_names = categories_names[-6:]
#     else:
#         for link in soup.find('div', class_='row tablet-rows').find_all('a'):
#             if ('Вся ' in link.text) or ('Все ' in link.text) or ('Новинки' in link.text) or (
#                     'Новые ' in link.text) or ('Всё ' in link.text):
#                 continue
#             else:
#                 categories_links.append(f'{url[:33]}{link["href"][7:]}')
#         for link in soup.find('div', class_='row tablet-rows').find_all('a'):
#             if ('Вся ' in link.text) or ('Все ' in link.text) or ('Новинки' in link.text) or (
#                     'Новые ' in link.text) or ('Всё ' in link.text):
#                 continue
#             else:
#                 categories_names.append(link.text)
#         counter = 0
#     for link in categories_links:             ----------------------------------------------------------------------------
#         category_name = categories_names[counter]
#         counter += 1
#         for i in range(1, 826):
#             category_url = link.strip('-0') + '?p=' + str(i)
#             item_soup = makingsouptxt(category_url)
#             print(category_url)
#             items = item_soup.find('div', "MuiGrid-root MuiGrid-container plp-product-grid-wrapper plp-1s9f1m4").find_all(
#                 'div', class_="MuiCardContent-root produc-1ivfcou")
#             if items:
#                 for item in items:
#                     nameid, price, *tale = item.find('a')['aria-label'].split(' | ')
#                     good_name = nameid[:nameid.find(' (')]
#                     good_id = nameid.rstrip(')').lstrip(' (')[-6:]
#                     good_link = item.find('a')['href']
#                     previoussib = item.previous_sibling
#                     image = previoussib.find('img')['src']
#                     if '-' in price or '&' in good_id:
#                         try:
#                             price_low = price.split(' - ')[0].strip(' тг').replace(' ', '')
#                             price_big = price.split(' - ')[1].strip(' тг').replace(' ', '')
#                             gooddict = {'id': good_id,
#                                         'name': good_name,
#                                         'price_low': price_low,
#                                         'price_big': price_big,
#                                         'link': good_link,
#                                         'image_path': image,
#                                         'availability': 'in_stock',
#                                         'primecategory_name': primecategory_name,
#                                         'category_name': category_name}
#                         except:
#                             brand, nameid, price, *tale = item.find('a')['aria-label'].split(' | ')
#                             good_name = nameid[:nameid.find(' (')]
#                             good_id = nameid.rstrip(')').lstrip(' (')[-6:]
#                             gooddict = {'id': good_id,
#                                         'name': good_name,
#                                         'price_low': price.strip('тг').replace(' ', ''),
#                                         'price_big': price.strip('тг').replace(' ', ''),
#                                         'link': good_link, 'image_path': image,
#                                         'availability': 'in_stock',
#                                         'primecategory_name': primecategory_name,
#                                         'category_name': category_name}
#                     else:
#                         gooddict = {'id': good_id,
#                                     'name': good_name,
#                                     'price_low': price.strip('тг').replace(' ', ''),
#                                     'price_big': price.strip('тг').replace(' ', ''),
#                                     'link': good_link,
#                                     'image_path': image, 'availability': 'in_stock',
#                                     'primecategory_name': primecategory_name,
#                                     'category_name': category_name}
#                     res.append(gooddict)
#                     id_list.append(gooddict['id'])
#                     id_set.add(gooddict['id'])
#             else:
#                 break
# with open('next.json', 'w', encoding='utf-8') as file:
#     json.dump(res, file, indent=4, ensure_ascii=False)
# with open('next_id.txt', 'w', encoding='utf-8') as file1:
#     for i in id_list:
#         file1.write(i + '\n')
# with open('next_idset.txt', 'w', encoding='utf-8') as file2:
#     for j in id_set:
#         file2.write(j + '\n')
# if len(id_set) == len(id_list):
#     print("Correct id's")
# else:
#     print('There some repeats in id')

from fake_useragent import UserAgent
import requests
import time
from bs4 import BeautifulSoup
import json


def makingsouptxt(urldef):
    ua = UserAgent()
    fake_ua = {'user-agent': ua.random}
    response = requests.get(url=urldef, headers=fake_ua)
    response.encoding = 'utf-8'
    return BeautifulSoup(response.text, 'lxml')


urlmain = 'https://www.nextdirect.com/kz/ru'
soupmain = makingsouptxt(urlmain)
primecategories = [f'{link["href"]}' for link in soupmain.find('ul', id='snail-trail-container').find_all('a')]
primecategories_names = [link.find('div', class_="header-5qe5c1").text for link in
                         soupmain.find('ul', id='snail-trail-container').find_all('a')]
primecounter = 0
del primecategories[5]
del primecategories_names[5]
res = []
id_list = []
id_set = set()
for primelink in primecategories[:-3]:
    url = primelink
    soup = makingsouptxt(url)
    primecategory_name = primecategories_names[primecounter]
    primecounter += 1
    # categories_links = [f'{url[:33]}{link["href"][7:]}' for link in
    #                     soup.find('div', class_='row tablet-rows').find_all('a') if
    #                     'Вся ' not in link.text and 'Все ' not in link.text and 'Новинки' not in link.text]
    categories_links = []
    # categories_names = [link.text for link in soup.find('div', class_='row tablet-rows').find_all('a') if
    #                     'Вся' not in link.text and 'Все' not in link.text and 'Новинки' not in link.text]
    categories_names = []
    if primelink == 'https://www.nextdirect.com/kz/ru/women':
        for link in soup.find_all('div', class_="sidebar-sec col-sm-12 col-md-3 col-lg-12"):
            women_links = link.find_all('a')
            for women_link in women_links:
                if 'Все Дамское белье' in women_link.text:
                    categories_links.append(f'{url[:33]}{women_link["href"][7:]}')
                elif ('Вся ' in women_link.text) or ('Все ' in women_link.text) or ('Новинки' in women_link.text) or (
                    'Новые ' in women_link.text) or ('Всё ' in women_link.text):
                    continue
                else:
                    categories_links.append(f'{url[:33]}{women_link["href"][7:]}')
            for women_link in women_links:
                if 'Все Дамское белье' in women_link.text:
                    categories_names.append(women_link.text)
                elif ('Вся ' in women_link.text) or ('Все ' in women_link.text) or ('Новинки' in women_link.text) or (
                    'Новые ' in women_link.text) or ('Всё ' in women_link.text):
                    continue
                else:
                    categories_names.append(women_link.text)
        counter = 0
        categories_links = categories_links[:15] + [categories_links[28]] + categories_links[31:]
        categories_names = categories_names[:15] + [categories_names[28]] + categories_names[31:]
    elif primelink == 'https://www.nextdirect.com/kz/ru/baby':
        link_list = soup.find_all('div', class_='row tablet-rows')[1]
        for link in link_list.find_all('a'):
            if ('Вся ' in link.text) or ('Все ' in link.text) or ('Новинки' in link.text) or (
                    'Новые ' in link.text) or ('Всё ' in link.text):
                continue
            else:
                categories_links.append(f'{url[:33]}{link["href"][7:]}')
        for link in link_list.find_all('a'):
            if ('Вся ' in link.text) or ('Все ' in link.text) or ('Новинки' in link.text) or (
                    'Новые ' in link.text) or ('Всё ' in link.text):
                continue
            else:
                categories_names.append(link.text)
        counter = 0
        categories_links = categories_links[-6:]
        categories_names = categories_names[-6:]
    else:
        for link in soup.find('div', class_='row tablet-rows').find_all('a'):
            if ('Вся ' in link.text) or ('Все ' in link.text) or ('Новинки' in link.text) or (
                    'Новые ' in link.text) or ('Всё ' in link.text):
                continue
            else:
                categories_links.append(f'{url[:33]}{link["href"][7:]}')
        for link in soup.find('div', class_='row tablet-rows').find_all('a'):
            if ('Вся ' in link.text) or ('Все ' in link.text) or ('Новинки' in link.text) or (
                    'Новые ' in link.text) or ('Всё ' in link.text):
                continue
            else:
                categories_names.append(link.text)
        counter = 0
    for link in categories_links:
        category_name = categories_names[counter]
        counter += 1
        for i in range(1, 826):
            category_url = link.strip('-0') + '?p=' + str(i)
            item_soup = makingsouptxt(category_url)
            print(category_url)
            items = item_soup.find('div', "MuiGrid-root MuiGrid-container plp-product-grid-wrapper plp-1s9f1m4").find_all(
                'div', class_="MuiCardContent-root produc-1ivfcou")
            if items:
                for item in items:
                    nameid, price, *tale = item.find('a')['aria-label'].split(' | ')
                    good_name = nameid[:nameid.find(' (')]
                    good_id = nameid.rstrip(')').lstrip(' (')[-6:]
                    good_link = item.find('a')['href']
                    previoussib = item.previous_sibling
                    image = previoussib.find('img')['src']
                    if '-' in price or '&' in good_id:
                        try:
                            price_low = price.split(' - ')[0].strip(' тг').replace(' ', '')
                            price_big = price.split(' - ')[1].strip(' тг').replace(' ', '')
                            gooddict = {'id': good_id,
                                        'name': good_name,
                                        'price_low': price_low,
                                        'price_big': price_big,
                                        'link': good_link,
                                        'image_path': image,
                                        'availability': 'in_stock',
                                        'primecategory_name': primecategory_name,
                                        'category_name': category_name}
                        except:
                            brand, nameid, price, *tale = item.find('a')['aria-label'].split(' | ')
                            good_name = nameid[:nameid.find(' (')]
                            good_id = nameid.rstrip(')').lstrip(' (')[-6:]
                            gooddict = {'id': good_id,
                                        'name': good_name,
                                        'price_low': price.strip('тг').replace(' ', ''),
                                        'price_big': price.strip('тг').replace(' ', ''),
                                        'link': good_link, 'image_path': image,
                                        'availability': 'in_stock',
                                        'primecategory_name': primecategory_name,
                                        'category_name': category_name}
                    else:
                        gooddict = {'id': good_id,
                                    'name': good_name,
                                    'price_low': price.strip('тг').replace(' ', ''),
                                    'price_big': price.strip('тг').replace(' ', ''),
                                    'link': good_link,
                                    'image_path': image, 'availability': 'in_stock',
                                    'primecategory_name': primecategory_name,
                                    'category_name': category_name}
                    res.append(gooddict)
                    id_list.append(gooddict['id'])
                    id_set.add(gooddict['id'])
            else:
                break
with open('next.json', 'w', encoding='utf-8') as file:
    json.dump(res, file, indent=4, ensure_ascii=False)
with open('next_id.txt', 'w', encoding='utf-8') as file1:
    for i in id_list:
        file1.write(i + '\n')
with open('next_idset.txt', 'w', encoding='utf-8') as file2:
    for j in id_set:
        file2.write(j + '\n')
if len(id_set) == len(id_list):
    print("Correct id's")
else:
    print('There some repeats in id')



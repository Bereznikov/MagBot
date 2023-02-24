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

# https://www.nextdirect.com/kz/ru/shop/gender-men-category-trousers/use-formal-0?p=101
item1 = 'https://www.nextdirect.com/kz/ru/shop/department-childrenswear/size-7480cm'
link = 'https://www.nextdirect.com/kz/ru/shop/department-childrenswear/size-7480cm'
for i in range(41, 826):
    category_url = link + '?p=' + str(i)
    item_soup = makingsouptxt(category_url)
    print(category_url)
    items = item_soup.find('div', "MuiGrid-root MuiGrid-container plp-product-grid-wrapper plp-1s9f1m4").find_all('div',
                                                                                                                  class_="MuiCardContent-root produc-1ivfcou")
    if items:
        for item in items:
            nameid, price, *tale = item.find('a')['aria-label'].split(' | ')
            good_name = nameid[:nameid.find(' (')]
            good_id = nameid[-6:].rstrip(')').lstrip(' (')
            good_link = item.find('a')['href']
            previoussib = item.previous_sibling
            image = previoussib.find('img')['src']
            if '-' in price:
                try:
                    price_low = price.split(' - ')[0].strip(' тг').replace(' ', '')
                    price_big = price.split(' - ')[1].strip(' тг').replace(' ', '')
                    gooddict = {'id': good_id, 'name': good_name, 'price_low': price_low, 'price_big': price_big,
                            'link': good_link,
                            'image_path': image, 'availability': 'in_stock'}
                except:
                    brand, nameid, price, *tale = item.find('a')['aria-label'].split(' | ')
                    good_name = nameid[:nameid.find(' (')]
                    good_id = nameid[-6:].rstrip(')').lstrip(' (')
                    gooddict = {'id': good_id, 'name': good_name, 'price': price.strip('тг').replace(' ', ''),
                                'link': good_link, 'image_path': image, 'availability': 'in_stock'}
            else:
                gooddict = {'id': good_id, 'name': good_name, 'price': price.strip('тг').replace(' ', ''),
                            'link': good_link, 'image_path': image, 'availability': 'in_stock'}
            print(gooddict)
    else:
        break

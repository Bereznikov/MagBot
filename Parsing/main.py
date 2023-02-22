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
primecategories_names = [link.find('div', class_="header-5qe5c1").text for link in soupmain.find('ul', id='snail-trail-container').find_all('a')]
primecounter = 0
del primecategories[5]
del primecategories_names[5]
res = []
for primelink in primecategories[:-3]:
    url = primelink
    soup = makingsouptxt(url)
    categories_links = [f'{url[:33]}{link["href"][7:]}' for link in soup.find('div', class_='row tablet-rows').find_all('a') if 'Вся' not in link.text and 'Все' not in link.text and 'Новинки' not in link.text]
    categories_names = [link.text for link in soup.find('div', class_='row tablet-rows').find_all('a') if 'Вся' not in link.text and 'Все' not in link.text and 'Новинки' not in link.text]
    counter = 0
    primecategory_name = primecategories_names[primecounter]
    primecounter += 1
    for link in categories_links:
        category_name = categories_names[counter]
        counter += 1
        for i in range(1, 826):
            category_url = link + '?p=' + str(i)
            item_soup = makingsouptxt(category_url)
            print(category_url)
            items = item_soup.find('div', "MuiGrid-root MuiGrid-container plp-product-grid-wrapper plp-1s9f1m4").find_all('div', class_= "MuiCardContent-root produc-1ivfcou")
            if items:
                for item in items:
                    nameid, price, *tale = item.find('a')['aria-label'].split(' | ')
                    good_name = nameid[:nameid.find(' (')]
                    good_id = nameid[-6:].rstrip(')').lstrip(' (')
                    good_link = item.find('a')['href']
                    previoussib = item.previous_sibling
                    image = previoussib.find('img')['src']
                    if '-' in price:
                        price_low = price.split(' - ')[0].strip(' тг').replace(' ', '')
                        price_big = price.split(' - ')[1].strip(' тг').replace(' ', '')
                        gooddict = {'id': good_id, 'name': good_name, 'price_low': price_low, 'price_big': price_big, 'link': good_link,
                                    'image_path': image, 'availability': 'in_stock',
                                    'primecategory_name': primecategory_name, 'category_name': category_name}
                    else:
                        gooddict = {'id': good_id, 'name': good_name,'price': price.strip('тг').replace(' ', ''), 'link': good_link, 'image_path': image, 'availability': 'in_stock', 'primecategory_name': primecategory_name, 'category_name': category_name}
                    res.append(gooddict)
            else:
                break
with open('../venv/next.json', 'w', encoding='utf-8') as file:
    json.dump(res, file, indent=4, ensure_ascii=False)

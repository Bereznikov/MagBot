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

res = []
url = 'https://www.nextdirect.com/kz/ru/men'
soup = makingsouptxt(url)
categories_links = [f'{url[:-3]}{link["href"]}' for link in soup.find('div', class_='row tablet-rows').find_all('a') if 'Вся' not in link.text and 'Все' not in link.text]

for link in categories_links:
    for i in range(1, 15):
        category_url = link + '?p=' + str(i)
        item_soup = makingsouptxt(category_url)
        print(category_url)
        items = item_soup.find('div', {'data-pagenumber': '1'}).find_all('section', class_= 'Details')
        for item in items:
            res.append([item.find('a')['title'].split(' | '), item.find('a')['href']])
            print(item.find('a')['title'].split(' | '), item.find('a')['href'])

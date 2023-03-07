import json


def make_next_json_with_category_id():
    with open('next.json', 'r') as file:
        next_product = json.load(file)
    with open('next_categories_redacted.json', 'r') as file:
        next_categories = json.load(file)
    next_categories_dict = {}
    for category in next_categories:
        next_categories_dict[category['subcategory']] = category['id']
    for product in next_product:
        if next_categories_dict.get(product['category_name'].upper()):
            product['category_id'] = next_categories_dict.get(product['category_name'].upper())
    # TODO
    # Ниже можно поменять название, чтобы не плодить файлы
    # Еще можно повторяющиеся ID удалить где-то тут
    with open('next_updated.json', "w") as file:
        json.dump(next_product, file, indent=4, ensure_ascii=False)


def main():
    make_next_json_with_category_id()


if __name__ == '__main__':
    main()

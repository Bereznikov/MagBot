import json

result = list()
result_set = set()
with open('next.json', 'r', encoding='utf-8') as file_next, open('zara_categories.json', 'r', encoding='utf-8') as file_zara:
    zara = file_zara.read()
    zara_dicts = json.loads(zara)
    content = file_next.read()
    next_dicts = json.loads(content)
    next_id = 1
    for item_next in next_dicts:
        for item_zara in zara_dicts:
            if item_next['category_name'].lower() == item_zara['subcategory'].lower() and item_next['primecategory_name'].lower() == item_zara['category'].lower():
                temp_set = (item_next['primecategory_name'].upper(), item_next['category_name'].upper())
                if temp_set not in result_set:
                    category_id = item_zara['id']
                    temp = {"category": item_next['primecategory_name'].upper(),
                            "subcategory": item_next['category_name'].upper(),
                            "id": category_id}
                    result_set.add(temp_set)
                    print(temp)
                    result.append(temp)
            else:
                temp_set = (item_next['primecategory_name'].upper(), item_next['category_name'].upper())
                if temp_set not in result_set:
                    space = '0' * (4 - len(str(next_id)))
                    temp = {"category": item_next['primecategory_name'].upper(),
                            "subcategory": item_next['category_name'].upper(),
                            "id": 'NXT' + space + str(next_id)}
                    result_set.add(temp_set)
                    print(temp)
                    result.append(temp)
                    next_id += 1
with open('next_categories.json', 'w', encoding='utf-8') as res_file:
        json.dump(result, res_file, indent=4, ensure_ascii=False)
print('end')



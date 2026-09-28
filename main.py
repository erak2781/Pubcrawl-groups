from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import math
import random
import io

app = Flask(__name__)
CORS(app)

def read_csv(csv_text: str, delimiter: str = ',', has_header: bool = True) -> list:
    reader = csv.reader(io.StringIO(csv_text), delimiter=delimiter)
    if has_header:
        next(reader, None)
    return list(reader)

# def read_csv(filename: csv) -> list:
#     result = []
#     with open(filename, 'r') as csv_file:
#         reader = csv.reader(csv_file)
#         for row in reader:
#             result.append(row)
#     return result


def create_dict(rows: list, name_col: int, partner_col) -> dict:
    result = {}
    for v in rows:
        if len(v) <= name_col or not v[name_col].strip():
            continue
        partner = ''
        if partner_col is not None and len(v) > partner_col:
            partner = v[partner_col].strip().lower()
        result[v[name_col].strip().lower()] = partner
    return result

def format_dict(name_dict: dict) -> list:
    new_list = []
    for x in name_dict.keys():
        name_1 = name_dict[x]
        if name_1 in name_dict and name_1 != '' and name_dict[name_1] == x:
            if [name_1, x] in new_list:
                continue
            else:
                print(f'pair {x}')
                print(name_1)
                new_list.append([x, name_1])
        else: 
            print(f'single {x}')
            new_list.append([x])

    new_list.sort(key=len, reverse=True)
    split = 0

    while(len(new_list[split]) > 1):
        split += 1
    pair_list = new_list[0: split]
    single_list = new_list[split:]
    print(f'Pair list: {pair_list}\n Single list: {single_list}')
    return pair_list, single_list

# def check_pair(name_dict: dict, name: String) -> bool:
#     if name_dict[name]:
#         name_1 = name_dict[name]
#         if name_dict[name_1] == name:
#             return True
#         else:
#             return False
#     else:
#         False

def usability_check(list: list, used_spaces: int, space: int) -> bool:
    if used_spaces + len(list) > space:
        return False
    else:
        return True


def create_groups(num_groups, csv_text, name_col, partner_col, has_header, delimiter) -> list:
    res_list = []

    name_dict = create_dict(read_csv(csv_text, delimiter, has_header), name_col, partner_col)
    pair_list, singel_list = format_dict(name_dict)
    ppl_per_group = math.floor(len(name_dict)/num_groups)
    remainder = len(name_dict) % num_groups

    for x in range(num_groups):
        res_list.append([])

    for x in range(len(res_list)):
        length = ppl_per_group
        if remainder > 0:
            length += 1
            remainder -= 1
        while ((pair_list or singel_list) and len(res_list[x]) < length):
            if pair_list and usability_check(pair_list[0], len(res_list[x]), length):
                res_list[x].append(pair_list[0][0])
                res_list[x].append(pair_list[0][1])
                del pair_list[0]
            elif singel_list:
                chosen = random.randint(0, len(singel_list) - 1)
                res_list[x].append(singel_list[chosen][0])
                del singel_list[chosen]
    print(res_list)
    print(singel_list)
    return res_list


@app.route('/api/generate-groups', methods=['POST'])
def generate_groups():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    num_groups = request.form.get('num_groups', type=int)

    if not num_groups or num_groups < 1:
        return jsonify({'error': 'Invalid number of groups'}), 400

    try:
        name_col = request.form.get('name_col', type=int)
        partner_col = request.form.get('partner_col', type=int)  # None if empty
        has_header = request.form.get('has_header', 'true') == 'true'
        delimiter = request.form.get('delimiter', ',')

        if name_col is None or name_col < 0:
            return jsonify({'error': 'Invalid name column'}), 400
        if name_col == partner_col:
            return jsonify({'error': 'Name and partner must be different columns'}), 400

        csv_text = file.read().decode('utf-8-sig')
        groups = create_groups(num_groups, csv_text, name_col, partner_col, has_header, delimiter)
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

# def print_groups(group_list: list) -> None:
#     i = 1
#     for x in group_list:
#         print(f'\nGrupp {i}:')
#         i += 1
#         for y in range(len(x)):
#             print(f'{x[y]}')
#         print(f'Group size: {len(x)}')
            
# filename = 'Namnlöst kalkylark - Blad1.csv'
# filename_2 = 'Pubrunda.csv'

# print_groups(create_groups(3, filename_2))

        

import csv
import io
import random
import math

def read_csv(csv_text: str, delimiter: str = ',', has_header: bool = True) -> list:
    reader = csv.reader(io.StringIO(csv_text), delimiter=delimiter)
    if has_header:
        next(reader, None)
    return list(reader)



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
                new_list.append([x, name_1])
        else: 
            new_list.append([x])

    new_list.sort(key=len, reverse=True)
    split = 0

    while(len(new_list[split]) > 1):
        split += 1
    pair_list = new_list[0: split]
    single_list = new_list[split:]
    return pair_list, single_list


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
    
    return res_list
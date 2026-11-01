from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import math
import random
import io
import openrouteservice
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
load_dotenv()

API_KEY = os.environ.get('ORS_API_KEY')

print(API_KEY)

uppsala_nations_coordinates = {
    "Stockholms Nation": [0, (59.856688632129746, 17.634177066153125)],
    "Uplands Nation": [1, (59.8598795147086, 17.62918785217144)],
    "Gästrike-Hälsingland Nation": [2, (59.85632310276747, 17.636613898196508)],
    "Östgöta Nation": [3, (59.855306459663595, 17.638174398196433)],
    "Västgöta Nation": [4, (59.85688037675121, 17.638629627031985)],
    "Västmanlands-Dala Nation": [5, (59.86032709023525, 17.62906333072819)],
    "Smålands Nation": [6, (59.8593319299539, 17.631203669361163)],
    "Göteborgs Nation": [7, (59.859488158774354, 17.63007714164067)],
    "Kalmar Nation": [8, (59.859163919860904, 17.627268503740748)],
    "Norrlands Nation": [9, (59.857382711345075, 17.637988401368933)],
    "Värmlands Nation": [10, (59.85721906916199, 17.633866737714456)],
    "Södermanlands-Nerikes Nation": [11, (59.85902485737546, 17.630624312247768)],
    "Gotlands Nation": [12, (59.85986361478064, 17.6345784270321)],
    "Skånes": [13, (59.85815523542735, 17.630653532192166)]
}

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

def get_ors_walking_distances(pubs: list):
    client = openrouteservice.Client(key=API_KEY)
    
    coordinates = [
        (lon, lat) for lat, lon in [uppsala_nations_coordinates[name][1] for name in pubs]
    ]

    response = client.distance_matrix(
    locations=coordinates,
    profile="foot-walking",  # Profile for walking directions
    metrics=["distance", "duration"],  # Requests both meters and seconds
    units="m",  # 'm' for meters, 'km' for kilometers
    )

    distances_m = response["distances"]
    sec = response["durations"]

    df_dist = pd.DataFrame(
    distances_m, index=pubs, columns=pubs
    )
    df_sec = pd.DataFrame(
        sec, index=pubs, columns=pubs
    )
    dist_dict = {k: distances_m[v] for v, k in enumerate(pubs)}
    index_translate = {k: v for v, k in enumerate(pubs)}
    print("Distances:")
    print(df_dist , '\n')

    print("Time:")
    print(df_sec)

    print(f'\n{dist_dict}')
    return dist_dict, index_translate


def closest_avg(lst: list, K: float):
    lst = np.average(lst)
    idx = (np.abs(lst - K)).argmin()
    return lst[idx]

def generate_paths(lst: list):
    ret_paths = [lst]
    for x in range(len(lst) - 2):
        new_path = ret_paths[-1].copy()
        new_last = new_path[1]
        new_path.remove(new_last)
        new_path.append(new_last)
        ret_paths.append(new_path)

    return ret_paths

def calculate_shortest_path(pubs: dict, translation: dict, start: str):
    path = [start]

    unvisited = set(pubs.keys())

    unvisited.remove(start)

    current = start
    while(unvisited):
        current_dist = pubs[current]

        choise = min(
                unvisited,
                key=lambda canditate: current_dist[translation[canditate]] 
         )

        path.append(choise)
        unvisited.remove(choise)
        current = choise

    paths = generate_paths(path)
    
    return paths



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

@app.route('/api/generate-path', methods=['POST'])
def generate_path():
    data = request.get_json(silent=True) or {}
    if not data or 'pubs' not in data:
        return jsonify({'error': 'missing pubs in list'}), 400

    pubs = data.get('pubs')
    if not isinstance(pubs, list) or len(pubs) < 2:
        return jsonify({'error': 'need more than 1 pub'}), 400
    invalid_pubs = [p for p in pubs if p not in uppsala_nations_coordinates]
    if invalid_pubs:
        return jsonify({'error': f'Cant find pubs {invalid_pubs}'}), 400
    start = data.get('start', pubs[0])
    if start not in pubs:
        return jsonify({'error': f'Start pub {start}, must be in pub list'}), 400
    try:
        dist_dict, index_translate = get_ors_walking_distances(pubs)


        paths = calculate_shortest_path(dist_dict, index_translate, start)

        return jsonify({
            'start' : start,
            'paths' : paths,
            'total_stops' : len(paths[0])
        }), 200
    except openrouteservice.exceptions.ApiError as e:
        return jsonify({'error': f'OpenRouteService API error: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

# pubs = ["Skånes", "Södermanlands-Nerikes Nation", "Stockholms Nation", "Östgöta Nation", "Västmanlands-Dala Nation"]
# dist_dict, index_translation =  get_ors_walking_distances(pubs)
# print(calculate_shortest_path(dist_dict, index_translation, "Skånes"))
        

import openrouteservice
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get('ORS_API_KEY')



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
    # print("Distances:")
    # print(df_dist , '\n')

    # print("Time:")
    # print(df_sec)

    # print(f'\n{dist_dict}')
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

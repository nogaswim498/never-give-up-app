import pandas as pd  
import math  
from datetime import datetime, timedelta  
  
# === 1. データ読み込みと高速化前処理 ===  
print("📂 Loading data...")  
try:  
    df_stops = pd.read_csv("data/stops.txt")  
    name_to_id = dict(zip(df_stops["stop_name"], df_stops["stop_id"]))  
    df_stops = df_stops.set_index("stop_id")  
      
    # 時刻表読み込み  
    df_times = pd.read_csv("data/stop_times.txt")  
      
    # ★高速化: Pandasの検索は遅いので、辞書(Hash Map)に変換しておく  
    # { "StationID": [ {row_data}, {row_data}... ], ... }  
    print("🚀 Optimizing timetable data...")  
    timetable_dict = {}  
      
    # stop_id でグループ化して辞書に格納  
    # これにより、駅名指定でのデータ取得が O(N) から O(1) になり爆速化  
    for stop_id, group in df_times.groupby("stop_id"):  
        timetable_dict[stop_id] = group.to_dict('records')  
          
    print(f"✅ Data ready: {len(timetable_dict)} stations have departures.")  
  
except FileNotFoundError:  
    print("❌ エラー: データファイルが見つかりません。")  
    # エラー時は空の辞書で動かす（落ちないように）  
    df_stops = pd.DataFrame()  
    timetable_dict = {}  
  
# === 2. ユーティリティ関数 ===  
  
def get_station_id_from_name(name):  
    if name in name_to_id: return name_to_id[name]  
    if name.endswith("駅") and name[:-1] in name_to_id: return name_to_id[name[:-1]]  
    return name  
  
def parse_time_to_minutes(time_str):  
    try:  
        parts = list(map(int, time_str.split(':')))  
        h, m = parts[0], parts[1]  
        if h >= 24: h -= 24  
        return h * 60 + m  
    except:  
        return 0  
  
def format_minutes_to_time(minutes):  
    h = (minutes // 60)  
    m = minutes % 60  
    if h < 5: h += 24  
    return f"{h:02d}:{m:02d}"  
  
def haversine_distance(lat1, lon1, lat2, lon2):  
    R = 6371  
    phi1, phi2 = math.radians(lat1), math.radians(lat2)  
    dphi = math.radians(lat2 - lat1)  
    dlambda = math.radians(lon2 - lon1)  
    term1 = math.sin(dphi / 2)**2  
    term2 = math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2  
    a = term1 + term2  
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))  
    return R * c  
  
def calculate_taxi_fare(km_distance, arrival_time_str):  
    road_km = km_distance * 1.4  
    meters = road_km * 1000  
    base_fare = 500  
    base_dist = 1096  
    if meters <= base_dist:  
        fare = base_fare  
    else:  
        add_dist = meters - base_dist  
        add_unit = 255  
        add_count = math.ceil(add_dist / add_unit)  
        fare = base_fare + (add_count * 100)  
      
    try:  
        h = int(arrival_time_str.split(':')[0])  
        is_night = (h >= 22 or h < 5 or h >= 24)  
        if is_night: fare = int(fare * 1.2)  
    except:  
        pass  
          
    fare = int(fare * 1.25)  
    return round(fare, -1)  
  
# === 3. 探索ロジック (高速化版) ===  
  
def search_routes(start_name, current_time_str, target_name=None, target_lat=None, target_lon=None):  
    start_id = get_station_id_from_name(start_name)  
    if start_id not in df_stops.index:  
        return {"error": f"出発駅 '{start_name}' がデータに見つかりません。"}  
  
    dest_lat = 0.0  
    dest_lon = 0.0  
  
    if target_lat is not None and target_lon is not None:  
        dest_lat = target_lat  
        dest_lon = target_lon  
    elif target_name:  
        target_id = get_station_id_from_name(target_name)  
        if target_id not in df_stops.index:  
            return {"error": f"到着駅 '{target_name}' がデータに見つかりません。"}  
        dest_lat = df_stops.loc[target_id, "stop_lat"]  
        dest_lon = df_stops.loc[target_id, "stop_lon"]  
    else:  
        return {"error": "目的地が指定されていません。"}  
  
    print(f"🔎 Search: {start_id} -> ({dest_lat}, {dest_lon})")  
      
    current_minutes = parse_time_to_minutes(current_time_str)  
      
    # BFS探索  
    reachable = {  
        start_id: {"arrival_time": current_minutes, "route": [start_id]}  
    }  
    queue = [start_id]  
      
    # 無限ループ防止用（探索回数制限）  
    explore_count = 0  
    MAX_EXPLORE = 2000   
  
    while queue and explore_count < MAX_EXPLORE:  
        current_station = queue.pop(0)  
        explore_count += 1  
          
        current_arrival = reachable[current_station]["arrival_time"]  
          
        # ★高速化: 辞書から一瞬で取得 (O(1))  
        departures = timetable_dict.get(current_station, [])  
          
        # 同じ路線の便をまとめて処理するためのキャッシュ  
        # trip_idごとに処理すると遅いので、行き先と時刻でフィルタリング  
          
        for dep_row in departures:  
            dep_time = parse_time_to_minutes(dep_row["departure_time"])  
              
            # まだ乗れる電車のみ  
            if dep_time >= current_arrival:  
                trip_id = dep_row["trip_id"]  
                dep_seq = dep_row["stop_sequence"]  
                  
                # この便の「次の駅」を探す  
                # ※ここも本来は辞書化すべきだが、データ構造上 trip_id で検索する必要がある  
                # 今回は stop_times 全体検索を避けるため、簡易的に「次の駅」データを持っていない場合はスキップ  
                # (本来は trip 単位の辞書も作るべきだが、メモリ節約のため省略)  
                  
                # ★簡易ロジック:  
                # この便(trip_id)の続きを取得するのは重いので、  
                # 「同じtrip_id」を持つレコードを df_times から探すのはNG。  
                # リアルタイム探索では限界があるため、  
                # 今回は「1駅進む」ことに特化して、全データスキャンを回避する実装は複雑になる。  
                # そのため、今回は「主要駅間」の移動のみを許容するか、  
                # あるいは「df_times」全体検索をやめて、事前に「trip_dict」を作る。  
                pass   
  
    # --- 再修正: 本格的な高速化には「Tripごとの辞書」も必要 ---  
    # 上記ループ内で df_times を検索すると遅いので、下記のアプローチに変えます。  
      
    return search_routes_optimized(start_id, current_minutes, dest_lat, dest_lon)  
  
# ★真・高速探索ロジック  
# グローバル変数として trip_dict を作る必要があります。  
# なので、ファイルの冒頭で作成しておきます。  
  
trip_dict = {} # { "trip_id": [ {stop_info}, {stop_info} ... (seq順) ] }  
  
# 初期化時に trip_dict も作る  
if 'df_times' in globals():  
    print("🚀 Indexing trips...")  
    for trip_id, group in df_times.groupby("trip_id"):  
        # stop_sequence順にソートしてリスト化  
        trip_dict[trip_id] = group.sort_values("stop_sequence").to_dict('records')  
    print(f"✅ Trips indexed: {len(trip_dict)}")  
  
def search_routes_optimized(start_id, start_time_min, dest_lat, dest_lon):  
    reachable = {  
        start_id: {"arrival_time": start_time_min, "route": [start_id]}  
    }  
    queue = [start_id]  
    processed_trips = set() # 同じ電車を何度も調べない  
      
    explore_count = 0  
    MAX_EXPLORE = 5000   
  
    while queue and explore_count < MAX_EXPLORE:  
        current_station = queue.pop(0)  
        explore_count += 1  
        current_arrival = reachable[current_station]["arrival_time"]  
          
        # この駅から出る全列車  
        departures = timetable_dict.get(current_station, [])  
          
        for dep in departures:  
            trip_id = dep["trip_id"]  
            if trip_id in processed_trips: continue # すでに乗った電車は無視  
              
            dep_time = parse_time_to_minutes(dep["departure_time"])  
              
            # 乗れるか？  
            if dep_time >= current_arrival:  
                processed_trips.add(trip_id) # この電車はもう調べたことにする  
                  
                # この電車の「現在地以降」の停車駅リストを取得  
                # trip_dict から一瞬で取れる  
                full_trip = trip_dict.get(trip_id, [])  
                  
                # 現在の駅が何番目か探す  
                current_seq = dep["stop_sequence"]  
                  
                # それ以降の駅を全て追加  
                for stop in full_trip:  
                    if stop["stop_sequence"] > current_seq:  
                        next_station = stop["stop_id"]  
                        arr_time = parse_time_to_minutes(stop["arrival_time"])  
                          
                        is_new = (next_station not in reachable)  
                        is_faster = False  
                        if not is_new:  
                            is_faster = (arr_time < reachable[next_station]["arrival_time"])  
                          
                        if is_new or is_faster:  
                            reachable[next_station] = {  
                                "arrival_time": arr_time,  
                                "route": reachable[current_station]["route"] + [next_station]  
                            }  
                            # 探索キューに追加（乗り換え用）  
                            # ただし終点や遠すぎる駅は追加しない等の間引きも可  
                            queue.append(next_station)  
  
    # 結果作成  
    results = []  
    for station_id, data in reachable.items():  
        # 出発地は除く（タクシーのみの案内はフロントエンドで行う）  
        if station_id == start_id: continue  
          
        # 駅情報がない場合はスキップ（stops.txtに含まれない駅など）  
        if station_id not in df_stops.index: continue  
  
        st_lat = df_stops.loc[station_id, "stop_lat"]  
        st_lon = df_stops.loc[station_id, "stop_lon"]  
        dist_km = haversine_distance(st_lat, st_lon, dest_lat, dest_lon)  
        arr_time_str = format_minutes_to_time(data["arrival_time"])  
        taxi_price = calculate_taxi_fare(dist_km, arr_time_str)  
        st_name_jp = df_stops.loc[station_id, "stop_name"]  
  
        results.append({  
            "station": st_name_jp,  
            "arrival_time": arr_time_str,  
            "distance_to_target_km": round(dist_km, 2),  
            "route_count": len(data["route"]),  
            "taxi_price": taxi_price,  
            "last_stop_id": station_id  
        })  
      
    results.sort(key=lambda x: x["taxi_price"])  
    return results  
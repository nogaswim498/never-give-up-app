import pandas as pd  
import math  
from datetime import datetime, timedelta  
  
# === 1. データ読み込み ===  
print("📂 Loading data...")  
try:  
    df_stops = pd.read_csv("data/stops.txt")  
    # 日本語名検索用に辞書を作る (例: "東京" -> "Tokyo")  
    name_to_id = dict(zip(df_stops["stop_name"], df_stops["stop_id"]))  
      
    # 検索高速化のためにIDをインデックスに  
    df_stops = df_stops.set_index("stop_id")  
      
    df_times = pd.read_csv("data/stop_times.txt")  
except FileNotFoundError:  
    print("❌ エラー: データファイルが見つかりません。")  
    exit()  
  
# === 2. ユーティリティ関数 ===  
  
def get_station_id_from_name(name):  
    """ 日本語駅名からIDを取得。見つからなければそのまま返す """  
    if name in name_to_id:  
        return name_to_id[name]  
    if name.endswith("駅") and name[:-1] in name_to_id:  
        return name_to_id[name[:-1]]  
    return name  
  
def parse_time_to_minutes(time_str):  
    parts = list(map(int, time_str.split(':')))  
    h, m = parts[0], parts[1]  
    if h >= 24: h -= 24  
    return h * 60 + m  
  
def format_minutes_to_time(minutes):  
    h = (minutes // 60)  
    m = minutes % 60  
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
  
# === 3. 探索ロジック ===  
  
def search_routes(start_name, current_time_str, target_name=None, target_lat=None, target_lon=None):  
    # 出発駅の名前をIDに変換  
    start_id = get_station_id_from_name(start_name)  
      
    if start_id not in df_stops.index:  
        return {"error": f"出発駅 '{start_name}' がデータに見つかりません。"}  
  
    # ターゲットの座標を確定させる  
    dest_lat = 0.0  
    dest_lon = 0.0  
  
    if target_lat is not None and target_lon is not None:  
        # 座標指定（自宅）の場合  
        dest_lat = target_lat  
        dest_lon = target_lon  
    elif target_name:  
        # 駅名指定の場合  
        target_id = get_station_id_from_name(target_name)  
        if target_id not in df_stops.index:  
            return {"error": f"到着駅 '{target_name}' がデータに見つかりません。"}  
        dest_lat = df_stops.loc[target_id, "stop_lat"]  
        dest_lon = df_stops.loc[target_id, "stop_lon"]  
    else:  
        return {"error": "目的地が指定されていません。"}  
  
    print(f"🔎 Search: {start_id} -> ({dest_lat}, {dest_lon}) @ {current_time_str}")  
      
    current_minutes = parse_time_to_minutes(current_time_str)  
      
    # BFS探索  
    reachable = {  
        start_id: {"arrival_time": current_minutes, "route": [start_id]}  
    }  
    queue = [start_id]  
      
    while queue:  
        current_station = queue.pop(0)  
        current_arrival = reachable[current_station]["arrival_time"]  
          
        departures = df_times[df_times["stop_id"] == current_station]  
          
        for _, dep_row in departures.iterrows():  
            trip_id = dep_row["trip_id"]  
            dep_time = parse_time_to_minutes(dep_row["departure_time"])  
            dep_seq = dep_row["stop_sequence"]  
              
            if dep_time >= current_arrival:  
                condition = (  
                    (df_times["trip_id"] == trip_id) &   
                    (df_times["stop_sequence"] > dep_seq)  
                )  
                trip_stops = df_times[condition]  
                  
                for _, arr_row in trip_stops.iterrows():  
                    next_station = arr_row["stop_id"]  
                    arr_time = parse_time_to_minutes(arr_row["arrival_time"])  
                      
                    is_new = (next_station not in reachable)  
                    is_faster = False  
                    if not is_new:  
                        is_faster = (arr_time < reachable[next_station]["arrival_time"])  
  
                    if is_new or is_faster:  
                        prev_route = reachable[current_station]["route"]  
                        reachable[next_station] = {  
                            "arrival_time": arr_time,  
                            "route": prev_route + [next_station]  
                        }  
                        queue.append(next_station)  
  
    # 結果作成  
    results = []  
    for station_id, data in reachable.items():  
        if station_id == start_id: continue  
          
        # 距離計算  
        st_lat = df_stops.loc[station_id, "stop_lat"]  
        st_lon = df_stops.loc[station_id, "stop_lon"]  
        dist = haversine_distance(st_lat, st_lon, dest_lat, dest_lon)  
          
        st_name_jp = df_stops.loc[station_id, "stop_name"]  
  
        results.append({  
            "station": st_name_jp,  
            "arrival_time": format_minutes_to_time(data["arrival_time"]),  
            "distance_to_target_km": round(dist, 2),  
            "route_count": len(data["route"]),  
            "last_stop_id": station_id  
        })  
      
    results.sort(key=lambda x: x["distance_to_target_km"])  
    return results  
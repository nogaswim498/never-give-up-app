import pandas as pd  
import math  
from datetime import datetime, timedelta  
  
# === 1. データ読み込み ===  
print("📂 Loading data...")  
try:  
    df_stops = pd.read_csv("data/stops.txt")  
    name_to_id = {}  
    for _, row in df_stops.iterrows():  
        name_to_id[row["stop_name"]] = row["stop_id"]  
        if row["stop_name"].endswith("駅"):  
            name_to_id[row["stop_name"][:-1]] = row["stop_id"]  
              
    df_stops = df_stops.set_index("stop_id")  
      
    # 時刻表  
    df_times = pd.read_csv("data/stop_times.txt")  
      
    # 辞書化  
    timetable_dict = {}  
    for stop_id, group in df_times.groupby("stop_id"):  
        timetable_dict[stop_id] = group.to_dict('records')  
          
    trip_dict = {}  
    for trip_id, group in df_times.groupby("trip_id"):  
        trip_dict[trip_id] = group.sort_values("stop_sequence").to_dict('records')  
          
    print(f"✅ Ready: {len(timetable_dict)} stations")  
  
except FileNotFoundError:  
    print("❌ Error: Data not found.")  
    name_to_id = {}  
    timetable_dict = {}  
    trip_dict = {}  
  
# === 2. ユーティリティ ===  
  
def get_station_id_from_name(name):  
    if name in name_to_id: return name_to_id[name]  
    if name.endswith("駅") and name[:-1] in name_to_id: return name_to_id[name[:-1]]  
    if not name.endswith("駅") and (name+"駅") in name_to_id: return name_to_id[name+"駅"]  
    return name  
  
def parse_time_to_minutes(time_str):  
    try:  
        # "24:30:00" -> 1470  
        parts = list(map(int, time_str.split(':')))  
        h, m = parts[0], parts[1]  
        # データ生成時に既に24時加算されている前提  
        return h * 60 + m  
    except: return 99999  
  
def format_minutes_to_time(minutes):  
    """ 分を HH:MM 表記に戻す (24時越え対応) """  
    h = (minutes // 60)  
    m = minutes % 60  
    # 24時を超えていたらそのまま表示 (例: 25:10)  
    # バグ修正: ゼロ埋めを確実に行う  
    return f"{h:02d}:{m:02d}"  
  
def haversine_distance(lat1, lon1, lat2, lon2):  
    R = 6371  
    phi1, phi2 = math.radians(lat1), math.radians(lat2)  
    dphi = math.radians(lat2 - lat1)  
    dlambda = math.radians(lon2 - lon1)  
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2  
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))  
    return R * c  
  
def calculate_taxi_fare(km_distance, arrival_time_str):  
    if km_distance < 0.1: return 0 # 距離ゼロなら無料  
    road_km = km_distance * 1.4  
    base_fare = 500  
    base_dist = 1.096  
      
    if road_km <= base_dist: fare = base_fare  
    else:  
        fare = base_fare + (math.ceil(((road_km - base_dist) * 1000) / 255) * 100)  
      
    try:  
        h = int(arrival_time_str.split(':')[0])  
        if h >= 22 or h < 5 or h >= 24: fare = int(fare * 1.2)  
    except: pass  
      
    return round(fare * 1.1, -1)  
  
# === 3. 探索ロジック ===  
  
def search_routes(start_name, current_time_str, target_name=None, target_lat=None, target_lon=None):  
    start_id = get_station_id_from_name(start_name)  
    if start_id not in name_to_id:  
        return {"error": f"出発駅 '{start_name}' が見つかりません。"}  
  
    dest_lat, dest_lon = 0.0, 0.0  
    if target_lat:  
        dest_lat, dest_lon = target_lat, target_lon  
    elif target_name:  
        tid = get_station_id_from_name(target_name)  
        if tid in df_stops.index:  
            dest_lat = df_stops.loc[tid, "stop_lat"]  
            dest_lon = df_stops.loc[tid, "stop_lon"]  
      
    if dest_lat == 0: return {"error": "目的地が不明です。"}  
  
    print(f"🔎 Search: {start_id} -> Target ({current_time_str})")  
      
    # ユーザー入力(0:30)を24:30に変換して検索  
    parts = list(map(int, current_time_str.split(':')))  
    h, m = parts[0], parts[1]  
    if h < 4: h += 24  
    current_minutes = h * 60 + m  
      
    # BFS  
    reachable = {start_id: {"arrival_time": current_minutes, "route": [start_id]}}  
    queue = [start_id]  
    processed_trips = set()  
      
    MAX_EXPLORE = 10000   
    count = 0  
  
    while queue and count < MAX_EXPLORE:  
        curr = queue.pop(0)  
        count += 1  
        curr_arr = reachable[curr]["arrival_time"]  
          
        # 翌朝まで行ったら打ち切り  
        if curr_arr > 1800: continue   
  
        departures = timetable_dict.get(curr, [])  
          
        for dep in departures:  
            trip_id = dep["trip_id"]  
            if trip_id in processed_trips: continue  
              
            dep_time = parse_time_to_minutes(dep["departure_time"])  
              
            # まだ出発していない電車に乗る  
            if dep_time >= curr_arr:  
                processed_trips.add(trip_id)  
                  
                full_trip = trip_dict.get(trip_id, [])  
                curr_seq = dep["stop_sequence"]  
                  
                for stop in full_trip:  
                    if stop["stop_sequence"] > curr_seq:  
                        next_st = stop["stop_id"]  
                        arr_time = parse_time_to_minutes(stop["arrival_time"])  
                          
                        is_new = (next_st not in reachable)  
                        is_faster = False  
                        if not is_new:  
                            is_faster = (arr_time < reachable[next_st]["arrival_time"])  
                          
                        if is_new or is_faster:  
                            reachable[next_st] = {  
                                "arrival_time": arr_time,  
                                "route": reachable[curr]["route"] + [next_st]  
                            }  
                            queue.append(next_st)  
  
    # 結果集計  
    results = []  
    if start_id in df_stops.index:  
        slat = df_stops.loc[start_id, "stop_lat"]  
        slon = df_stops.loc[start_id, "stop_lon"]  
        start_dist = haversine_distance(slat, slon, dest_lat, dest_lon)  
    else:  
        start_dist = 9999  
  
    for sid, data in reachable.items():  
        if sid == start_id: continue  
        if sid not in df_stops.index: continue  
          
        lat = df_stops.loc[sid, "stop_lat"]  
        lon = df_stops.loc[sid, "stop_lon"]  
        dist = haversine_distance(lat, lon, dest_lat, dest_lon)  
          
        # 近づいた駅のみ (距離が短くなっていること)  
        if dist < start_dist:  
            arr_str = format_minutes_to_time(data["arrival_time"])  
            price = calculate_taxi_fare(dist, arr_str)  
              
            results.append({  
                "station": sid,  
                "arrival_time": arr_str,  
                "distance_to_target_km": round(dist, 2),  
                "route_count": len(data["route"]),  
                "taxi_price": price,  
                "last_stop_id": sid  
            })  
              
    results.sort(key=lambda x: x["distance_to_target_km"])  
    return results[:10]  
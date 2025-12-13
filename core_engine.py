import pandas as pd  
import math  
from datetime import datetime, timedelta  
  
# === 1. データ読み込み ===  
print("📂 Loading data...")  
try:  
    df_stops = pd.read_csv("data/stops.txt")  
    # 検索用マップ: 名前そのままと、"駅"を除いたもの両方登録  
    name_to_id = {}  
    for _, row in df_stops.iterrows():  
        name_to_id[row["stop_name"]] = row["stop_id"]  
        if row["stop_name"].endswith("駅"):  
            name_to_id[row["stop_name"][:-1]] = row["stop_id"]  
              
    df_stops = df_stops.set_index("stop_id")  
      
    # 時刻表読み込み  
    df_times = pd.read_csv("data/stop_times.txt")  
      
    # 高速化: 辞書変換  
    print("🚀 Optimizing timetable data...")  
    timetable_dict = {}  
    for stop_id, group in df_times.groupby("stop_id"):  
        timetable_dict[stop_id] = group.to_dict('records')  
          
    # Tripごとの辞書（乗り換え探索用）  
    trip_dict = {}  
    for trip_id, group in df_times.groupby("trip_id"):  
        trip_dict[trip_id] = group.sort_values("stop_sequence").to_dict('records')  
          
    print(f"✅ Data ready: {len(timetable_dict)} stations, {len(trip_dict)} trips.")  
  
except FileNotFoundError:  
    print("❌ エラー: データファイルが見つかりません。")  
    df_stops = pd.DataFrame()  
    timetable_dict = {}  
    trip_dict = {}  
  
# === 2. ユーティリティ関数 ===  
  
def get_station_id_from_name(name):  
    if name in name_to_id: return name_to_id[name]  
    if name.endswith("駅") and name[:-1] in name_to_id: return name_to_id[name[:-1]]  
    if not name.endswith("駅") and (name+"駅") in name_to_id: return name_to_id[name+"駅"]  
    return name  
  
def parse_time_to_minutes(time_str):  
    """  
    時刻文字列を分に変換する。  
    ★重要修正: 00:00〜03:59 は 24:00〜27:59 (深夜延長) として扱う  
    """  
    try:  
        parts = list(map(int, time_str.split(':')))  
        h, m = parts[0], parts[1]  
          
        # データが "00:15" の場合、23:59より未来と判定させるために "24:15" 扱いにする  
        if h < 4:  
            h += 24  
              
        return h * 60 + m  
    except:  
        return 99999  
  
def format_minutes_to_time(minutes):  
    """ 分を HH:MM 表記に戻す (24時越え対応) """  
    h = (minutes // 60)  
    m = minutes % 60  
    # 24時を超えていたらそのまま表示 (例: 25:10)  
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
        # 深夜割増判定  
        # arrival_time_str は "25:10" のようになっている可能性がある  
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
        return {"error": f"出発駅 '{start_name}' (ID:{start_id}) のデータがありません。"}  
  
    dest_lat = 0.0  
    dest_lon = 0.0  
  
    if target_lat is not None and target_lon is not None:  
        dest_lat = target_lat  
        dest_lon = target_lon  
    elif target_name:  
        target_id = get_station_id_from_name(target_name)  
        if target_id not in df_stops.index:  
            return {"error": f"到着駅 '{target_name}' のデータがありません。"}  
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
    processed_trips = set()  
      
    explore_count = 0  
    MAX_EXPLORE = 30000 # 探索上限をさらに緩和  
  
    while queue and explore_count < MAX_EXPLORE:  
        current_station = queue.pop(0)  
        explore_count += 1  
        current_arrival = reachable[current_station]["arrival_time"]  
          
        # 翌日の昼(30時間=1800分)を超えたら探索打ち切り  
        if current_arrival > 1800: continue  
  
        departures = timetable_dict.get(current_station, [])  
          
        for dep in departures:  
            trip_id = dep["trip_id"]  
            if trip_id in processed_trips: continue  
              
            dep_time = parse_time_to_minutes(dep["departure_time"])  
              
            # 乗れるか？ (現在時刻以降)  
            if dep_time >= current_arrival:  
                processed_trips.add(trip_id)  
                  
                full_trip = trip_dict.get(trip_id, [])  
                current_seq = dep["stop_sequence"]  
                  
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
                            queue.append(next_station)  
  
    # 結果作成  
    results = []  
    for station_id, data in reachable.items():  
        if station_id == start_id: continue  
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
      
    # 料金が安い順（または距離が近い順）  
    results.sort(key=lambda x: x["taxi_price"])  
    return results  
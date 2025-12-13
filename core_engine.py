import pandas as pd  
import math  
from datetime import datetime, timedelta  
  
# === 1. データ読み込み ===  
print("📂 Loading data...")  
try:  
    df_stops = pd.read_csv("data/stops.txt")  
    name_to_id = dict(zip(df_stops["stop_name"], df_stops["stop_id"]))  
    df_stops = df_stops.set_index("stop_id")  
    df_times = pd.read_csv("data/stop_times.txt")  
except FileNotFoundError:  
    print("❌ エラー: データファイルが見つかりません。")  
    exit()  
  
# === 2. ユーティリティ関数 ===  
  
def get_station_id_from_name(name):  
    if name in name_to_id: return name_to_id[name]  
    if name.endswith("駅") and name[:-1] in name_to_id: return name_to_id[name[:-1]]  
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
    """ 2点間の直線距離(km) """  
    R = 6371  
    phi1, phi2 = math.radians(lat1), math.radians(lat2)  
    dphi = math.radians(lat2 - lat1)  
    dlambda = math.radians(lon2 - lon1)  
    term1 = math.sin(dphi / 2)**2  
    term2 = math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2  
    a = term1 + term2  
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))  
    return R * c  
  
# === ★新機能: 厳密なタクシー料金計算ロジック ===  
def calculate_taxi_fare(km_distance, is_night=True):  
    """  
    東京地区の公定運賃に近い計算を行う  
    is_night: 深夜割増(22時-5時)を適用するか  
    """  
    # 1. 道路距離への補正 (直線距離 x 1.3倍)  
    road_km = km_distance * 1.3  
      
    # メートル換算  
    meters = road_km * 1000  
      
    # 2. 運賃計算 (2022年改定後の東京特定区準拠: 初乗り1.096km 500円)  
    base_fare = 500  
    base_dist = 1096  
      
    if meters <= base_dist:  
        fare = base_fare  
    else:  
        # 加算距離: 255mごとに100円  
        add_dist = meters - base_dist  
        add_unit = 255  
        add_count = math.ceil(add_dist / add_unit)  
        fare = base_fare + (add_count * 100)  
      
    # 3. 深夜割増 (2割増)  
    if is_night:  
        fare = int(fare * 1.2)  
      
    # 10円単位に丸める（タクシー仕様）  
    return round(fare, -1)  
  
# === 3. 探索ロジック ===  
  
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
  
    # 時間帯判定（深夜割増用）: 4時前なら深夜とみなす  
    h = int(current_time_str.split(':')[0])  
    is_night_time = (h >= 22 or h < 5 or h >= 24)  
  
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
                condition = ((df_times["trip_id"] == trip_id) & (df_times["stop_sequence"] > dep_seq))  
                trip_stops = df_times[condition]  
                for _, arr_row in trip_stops.iterrows():  
                    next_station = arr_row["stop_id"]  
                    arr_time = parse_time_to_minutes(arr_row["arrival_time"])  
                    is_new = (next_station not in reachable)  
                    is_faster = False  
                    if not is_new: is_faster = (arr_time < reachable[next_station]["arrival_time"])  
  
                    if is_new or is_faster:  
                        prev_route = reachable[current_station]["route"]  
                        reachable[next_station] = {  
                            "arrival_time": arr_time,  
                            "route": prev_route + [next_station]  
                        }  
                        queue.append(next_station)  
  
    results = []  
    for station_id, data in reachable.items():  
        if station_id == start_id: continue  
          
        # 直線距離  
        st_lat = df_stops.loc[station_id, "stop_lat"]  
        st_lon = df_stops.loc[station_id, "stop_lon"]  
        dist_km = haversine_distance(st_lat, st_lon, dest_lat, dest_lon)  
          
        # ★ここで厳密なタクシー料金を計算  
        taxi_price = calculate_taxi_fare(dist_km, is_night=is_night_time)  
          
        st_name_jp = df_stops.loc[station_id, "stop_name"]  
  
        results.append({  
            "station": st_name_jp,  
            "arrival_time": format_minutes_to_time(data["arrival_time"]),  
            "distance_to_target_km": round(dist_km, 2), # 表示は直線距離のままでOK（目安）  
            "route_count": len(data["route"]),  
            "taxi_price": taxi_price, # 追加: サーバー側で計算した正確な料金  
            "last_stop_id": station_id  
        })  
      
    # 料金が安い順、あるいは距離が近い順にソート（今回は距離優先）  
    results.sort(key=lambda x: x["distance_to_target_km"])  
    return results  
import pandas as pd  
import math  
  
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
    # 24時越え対応  
    if h >= 24: h -= 24  
    return h * 60 + m  
  
def format_minutes_to_time(minutes):  
    h = (minutes // 60)  
    m = minutes % 60  
    # 24時を超えたら24:xx表記にする（深夜の実感を持たせるため）  
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
  
# === ★修正: タクシー料金計算ロジック（辛口設定） ===  
def calculate_taxi_fare(km_distance, arrival_time_str):  
    """  
    GOアプリ等の実勢価格に近づけるための補正入り計算  
    """  
    # 1. 道路距離への補正 (直線距離 x 1.4倍)  
    # 実際の道路は直線よりかなり長い + 高速利用などの可能性  
    road_km = km_distance * 1.4  
      
    # メートル換算  
    meters = road_km * 1000  
      
    # 2. 運賃計算 (東京特定区準拠)  
    base_fare = 500  
    base_dist = 1096  
      
    if meters <= base_dist:  
        fare = base_fare  
    else:  
        add_dist = meters - base_dist  
        add_unit = 255  
        add_count = math.ceil(add_dist / add_unit)  
        fare = base_fare + (add_count * 100)  
      
    # 3. 深夜割増判定 (到着時刻ベース)  
    # 文字列 "23:39" や "24:05" から時間を取得  
    h = int(arrival_time_str.split(':')[0])  
    # 22時〜5時は割増 (24時表記対応)  
    is_night = (h >= 22 or h < 5 or h >= 24)  
      
    if is_night:  
        fare = int(fare * 1.2)  
      
    # 4. 実勢価格補正 (迎車料金、信号待ち、渋滞などの時間距離併用運賃分)  
    # これを入れないと安く出過ぎるため、さらに1.25倍する  
    fare = int(fare * 1.25)  
      
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
  
    print(f"🔎 Search: {start_id} -> ({dest_lat}, {dest_lon})")  
      
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
        # ★修正: 出発駅も候補に含める (電車に乗らずタクシーに乗る選択肢)  
        # if station_id == start_id: continue   
          
        st_lat = df_stops.loc[station_id, "stop_lat"]  
        st_lon = df_stops.loc[station_id, "stop_lon"]  
        dist_km = haversine_distance(st_lat, st_lon, dest_lat, dest_lon)  
          
        # 到着時刻の文字列を作る  
        arr_time_str = format_minutes_to_time(data["arrival_time"])  
          
        # 料金計算に到着時刻を渡す（深夜判定用）  
        taxi_price = calculate_taxi_fare(dist_km, arr_time_str)  
          
        st_name_jp = df_stops.loc[station_id, "stop_name"]  
  
        # 評価スコア: タクシー料金が安い順を優先するが、移動回数も考慮  
        # ここではシンプルに「タクシー料金」を主な指標にする  
        results.append({  
            "station": st_name_jp,  
            "arrival_time": arr_time_str,  
            "distance_to_target_km": round(dist_km, 2),  
            "route_count": len(data["route"]),  
            "taxi_price": taxi_price,  
            "last_stop_id": station_id  
        })  
      
    # 並び替え: タクシー料金が安い順  
    results.sort(key=lambda x: x["taxi_price"])  
    return results  
import pandas as pd  
import math  
from datetime import datetime, timedelta  
  
# === 1. データ読み込み ===  
print("📂 Loading data...")  
try:  
    # 駅データ (IDをキーにする)  
    df_stops = pd.read_csv("data/stops.txt").set_index("stop_id")  
    # 時刻表データ  
    df_times = pd.read_csv("data/stop_times.txt")  
except FileNotFoundError:  
    print("❌ エラー: データファイルが見つかりません。Step 1を実行しましたか？")  
    exit()  
  
# === 2. ユーティリティ関数 ===  
  
def parse_time_to_minutes(time_str):  
    """ 'HH:MM:SS' または 'HH:MM' を「00:00からの経過分」に変換 """  
    parts = list(map(int, time_str.split(':')))  
    h, m = parts[0], parts[1]  
    # 深夜24時以降の扱い  
    if h >= 24:  
        h -= 24  
    return h * 60 + m  
  
def format_minutes_to_time(minutes):  
    """ 分を 'HH:MM' 表記に戻す """  
    h = (minutes // 60)  
    m = minutes % 60  
    return f"{h:02d}:{m:02d}"  
  
def haversine_distance(lat1, lon1, lat2, lon2):  
    """ 2点間の緯度経度から距離(km)を計算 """  
    R = 6371  # 地球の半径 (km)  
    phi1, phi2 = math.radians(lat1), math.radians(lat2)  
    dphi = math.radians(lat2 - lat1)  
    dlambda = math.radians(lon2 - lon1)  
      
    # 計算式を整理  
    term1 = math.sin(dphi / 2)**2  
    term2 = math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2  
    a = term1 + term2  
           
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))  
    return R * c  
  
# === 3. 探索ロジック (Time-Dependent BFS) ===  
  
def search_routes(start_id, target_id, current_time_str):  
    print(f"🔎 Searching routes from {start_id} to {target_id} after {current_time_str}...")  
      
    current_minutes = parse_time_to_minutes(current_time_str)  
      
    # ターゲット駅の座標  
    target_lat = df_stops.loc[target_id, "stop_lat"]  
    target_lon = df_stops.loc[target_id, "stop_lon"]  
  
    # 到達可能な駅を管理する辞書  
    # key: stop_id, value: {arrival_time: 分, route: [駅リスト]}  
    reachable = {  
        start_id: {"arrival_time": current_minutes, "route": [start_id]}  
    }  
      
    queue = [start_id] # 探索キュー  
      
    while queue:  
        current_station = queue.pop(0)  
        current_arrival = reachable[current_station]["arrival_time"]  
          
        # この駅から出発するすべての便を探す  
        departures = df_times[df_times["stop_id"] == current_station]  
          
        for _, dep_row in departures.iterrows():  
            trip_id = dep_row["trip_id"]  
            dep_time = parse_time_to_minutes(dep_row["departure_time"])  
            dep_seq = dep_row["stop_sequence"]  
              
            # まだ乗れる電車か？  
            if dep_time >= current_arrival:  
                # この便(trip_id)の「次の駅以降」を取得  
                # 括弧で囲むことで安全に改行  
                condition = (  
                    (df_times["trip_id"] == trip_id) &   
                    (df_times["stop_sequence"] > dep_seq)  
                )  
                trip_stops = df_times[condition]  
                  
                for _, arr_row in trip_stops.iterrows():  
                    next_station = arr_row["stop_id"]  
                    arr_time = parse_time_to_minutes(arr_row["arrival_time"])  
                      
                    # より早く着ける、または未到達の駅なら更新  
                    # ここも括弧で囲んで安全に記述  
                    is_new_station = (next_station not in reachable)  
                    is_faster_arrival = False  
                    if not is_new_station:  
                        is_faster_arrival = (arr_time < reachable[next_station]["arrival_time"])  
  
                    if is_new_station or is_faster_arrival:  
                        # ルート更新  
                        prev_route = reachable[current_station]["route"]  
                        reachable[next_station] = {  
                            "arrival_time": arr_time,  
                            "route": prev_route + [next_station]  
                        }  
                        queue.append(next_station)  
  
    # === 4. 結果の評価と整形 ===  
    results = []  
      
    for station_id, data in reachable.items():  
        if station_id == start_id: continue # 出発地は除外  
          
        # 目的地までの距離を計算  
        st_lat = df_stops.loc[station_id, "stop_lat"]  
        st_lon = df_stops.loc[station_id, "stop_lon"]  
        dist = haversine_distance(st_lat, st_lon, target_lat, target_lon)  
          
        results.append({  
            "station": df_stops.loc[station_id, "stop_name"],  
            "arrival_time": format_minutes_to_time(data["arrival_time"]),  
            "distance_to_target_km": round(dist, 2),  
            "route_count": len(data["route"]),  
            "last_stop_id": station_id  
        })  
      
    # 目的地に近い順にソート  
    results.sort(key=lambda x: x["distance_to_target_km"])  
    return results  
  
# === 実行テスト ===  
  
if __name__ == "__main__":  
    # シナリオ設定  
    START_NODE = "Shibuya"  
    TARGET_NODE = "Yokohama"  
    CURRENT_TIME = "24:40" # 深夜 00:40  
  
    candidates = search_routes(START_NODE, TARGET_NODE, CURRENT_TIME)  
  
    print("\n" + "="*40)  
    print(f"🧞 結果発表: {CURRENT_TIME}発 {START_NODE} → {TARGET_NODE}")  
    print("="*40)  
  
    if not candidates:  
        print("😱 残念ながら、一歩も動けません。")  
    else:  
        # 目的地に到着できたかチェック  
        reached_target = any(c["station"] == "横浜" for c in candidates)  
          
        if reached_target:  
            print("✅ 奇跡的に目的地まで行けます！通常ルート案内を表示します。")  
        else:  
            print("⚠️ 目的地には到達できませんでした。")  
            print("👇 行けるところまでの候補（近い順）:")  
            for i, c in enumerate(candidates[:3]): # 上位3件  
                print(f"{i+1}. {c['station']} 駅")  
                print(f"   到着: {c['arrival_time']}")  
                print(f"   横浜まで残り: {c['distance_to_target_km']} km")  
                print(f"   ----------------")  
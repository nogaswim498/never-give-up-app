import requests  
import pandas as pd  
import json  
import os  
import time  
import math  # これが必須です  
  
# ==========================================  
# ★ここにODPTのAPIキーを入れてください  
API_KEY = "pvljcnxsfstd3z41mu5uiewsrryz36f5o66yn5axpmosqbt3jgm2ghn0boz5jsn3"  
# ==========================================  
    
      
DATA_DIR = "data"  
os.makedirs(DATA_DIR, exist_ok=True)  
  
TARGET_OPERATORS = [  
    "odpt.Operator:TokyoMetro", "odpt.Operator:Toei", "odpt.Operator:JR-East",  
    "odpt.Operator:Tokyu", "odpt.Operator:Odakyu", "odpt.Operator:Keio",  
    "odpt.Operator:Seibu", "odpt.Operator:Tobu", "odpt.Operator:Sotetsu",  
    "odpt.Operator:Keikyu", "odpt.Operator:Yurikamome", "odpt.Operator:TWR",  
    "odpt.Operator:YokohamaMunicipal", "odpt.Operator:MIR"  
]  
  
API_BASE = "https://api.odpt.org/api/v4"  
  
def safe_haversine(g1, g2):  
    try:  
        R = 6371  
        lat1, lon1 = math.radians(g1["lat"]), math.radians(g1["lon"])  
        lat2, lon2 = math.radians(g2["lat"]), math.radians(g2["lon"])  
        d = 2 * R * math.asin(math.sqrt(math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2))  
        return d  
    except: return 2.0  
  
def add_minutes(time_str, mins):  
    try:  
        h, m = map(int, time_str.split(':')[:2])  
        m += mins  
        h += m // 60  
        m %= 60  
        return f"{h:02d}:{m:02d}:00"  
    except: return time_str  
  
def fetch_all_data():  
    print("🚀 ODPTから全路線のデータを取得します (確実性重視モード)...")  
      
    station_map = {}     # ID -> 漢字駅名  
    station_geo_cache = {} # ID -> {lat, lon}  
    railway_map = {}     # RailwayID -> [StationID List]  
  
    # --- 1. 駅情報の取得 (事業者ごとに全件取得) ---  
    print("📡 駅定義を取得中...")  
    for op in TARGET_OPERATORS:  
        print(f"  ⏳ {op.split(':')[-1]} の駅を取得...", end="\r")  
        try:  
            # 事業者指定で全駅取る  
            res = requests.get(f"{API_BASE}/odpt:Station", params={"acl:consumerKey": API_KEY, "odpt:operator": op})  
            if res.status_code == 200:  
                stations = res.json()  
                for st in stations:  
                    sid = st["owl:sameAs"]  
                    title = st["dc:title"]  
                    station_map[sid] = title  
                    if "geo:lat" in st:  
                        station_geo_cache[sid] = {"lat": st["geo:lat"], "lon": st["geo:long"]}  
            else:  
                print(f"  ❌ {op} 駅取得エラー: {res.status_code}")  
        except Exception as e:  
            print(f"  ❌ {op} 駅取得例外: {e}")  
        time.sleep(0.1)  
      
    print(f"\n✅ 合計 {len(station_map)} 駅の定義をロードしました。")  
  
    # --- 2. 路線情報の取得 ---  
    print("📡 路線定義(駅順)を取得中...")  
    for op in TARGET_OPERATORS:  
        try:  
            res = requests.get(f"{API_BASE}/odpt:Railway", params={"acl:consumerKey": API_KEY, "odpt:operator": op})  
            if res.status_code == 200:  
                for rw in res.json():  
                    rid = rw["owl:sameAs"]  
                    st_list = rw.get("odpt:stationOrder", [])  
                    ordered_ids = [s["odpt:station"] if isinstance(s, dict) else s for s in st_list]  
                    railway_map[rid] = ordered_ids  
        except: pass  
      
    print(f"✅ {len(railway_map)} 路線の定義をロードしました。")  
  
    # --- 3. 時刻表データの生成 ---  
    all_stop_times = []  
      
    for rid, ordered_station_ids in railway_map.items():  
        line_name = rid.split(':')[-1]  
          
        # Aプラン: TrainTimetable  
        trains_found = False  
        try:  
            # 平日のみ取得  
            res = requests.get(f"{API_BASE}/odpt:TrainTimetable", params={  
                "acl:consumerKey": API_KEY, "odpt:railway": rid, "odpt:calendar": "odpt.Calendar:Weekday"  
            })  
            if res.status_code == 200:  
                trains = res.json()  
                if len(trains) > 0:  
                    trains_found = True  
                    for train in trains:  
                        tid = train["owl:sameAs"]  
                        for i, stop in enumerate(train.get("odpt:trainTimetableObject", [])):  
                            sid = stop.get("odpt:departureStation") or stop.get("odpt:arrivalStation")  
                            t_str = stop.get("odpt:departureTime") or stop.get("odpt:arrivalTime")  
                            if sid and t_str and (sid in station_map):  
                                if len(t_str) == 5: t_str += ":00"  
                                all_stop_times.append({  
                                    "trip_id": tid, "stop_id": station_map[sid],  
                                    "arrival_time": t_str, "departure_time": t_str, "stop_sequence": i+1  
                                })  
        except Exception as e:  
            print(f"  ❌ Error fetching trains for {line_name}: {e}")  
  
        # Bプラン: StationTimetable  
        if not trains_found:  
            gen_count = 0  
            # 駅リストがあれば、それに沿って取得  
            if ordered_station_ids:  
                targets = ordered_station_ids  
            else:  
                # 路線図がない場合、station_mapにある駅のうち、路線IDが一致しそうなものを総当たり(非効率だが救済策)  
                # 今回は station_map から逆引きは難しいのでスキップ  
                print(f"  ⚠️ {line_name}: 路線図(駅順)が不明なためスキップ")  
                continue  
  
            # 各駅についてループ  
            for curr_idx, current_sid in enumerate(targets):  
                if current_sid not in station_map: continue  
                  
                try:  
                    # この駅の時刻表を取得  
                    res = requests.get(f"{API_BASE}/odpt:StationTimetable", params={  
                        "acl:consumerKey": API_KEY,   
                        "odpt:station": current_sid,   
                        "odpt:railway": rid,  
                        "odpt:calendar": "odpt.Calendar:Weekday"  
                    })  
                    if res.status_code != 200: continue  
                      
                    st_tables = res.json()  
                    for stt in st_tables:  
                        for obj in stt.get("odpt:stationTimetableObject", []):  
                            dep_time = obj.get("odpt:departureTime")  
                            if not dep_time: continue  
                            if len(dep_time) == 5: dep_time += ":00"  
                              
                            dest = obj.get("odpt:destinationStation", [None])[0]  
                            direction = 0  
                            if dest and dest in targets:  
                                dest_idx = targets.index(dest)  
                                if dest_idx > curr_idx: direction = 1  
                                elif dest_idx < curr_idx: direction = -1  
                              
                            if direction == 0:  
                                if curr_idx < len(targets) - 1: direction = 1  
                                else: continue  
  
                            next_idx = curr_idx + direction  
                            if 0 <= next_idx < len(targets):  
                                next_sid = targets[next_idx]  
                                if next_sid in station_map:  
                                    travel_min = 2  
                                    if current_sid in station_geo_cache and next_sid in station_geo_cache:  
                                        dist = safe_haversine(station_geo_cache[current_sid], station_geo_cache[next_sid])  
                                        travel_min = max(1, round((dist / 40) * 60))  
                                      
                                    arr_time = add_minutes(dep_time, travel_min)  
                                    uid = f"t_{current_sid}_{dep_time}_{direction}"  
                                      
                                    all_stop_times.append({  
                                        "trip_id": uid, "stop_id": station_map[current_sid],  
                                        "arrival_time": dep_time, "departure_time": dep_time, "stop_sequence": 1  
                                    })  
                                    all_stop_times.append({  
                                        "trip_id": uid, "stop_id": station_map[next_sid],  
                                        "arrival_time": arr_time, "departure_time": arr_time, "stop_sequence": 2  
                                    })  
                                    gen_count += 1  
                    # 連続アクセス負荷軽減  
                    # time.sleep(0.01)   
                except: pass  
              
            if gen_count > 0:  
                print(f"  ✅ {line_name}: {gen_count} 区間生成 (StationTimetable)")  
            else:  
                print(f"  ⚠️ {line_name}: データなし (API制限またはデータ未提供)")  
        else:  
            print(f"  ✅ {line_name}: TrainTimetable 取得成功")  
  
    # 4. 保存  
    if not all_stop_times:  
        print("❌ データが生成されませんでした。")  
        return  
  
    print(f"\n💾 CSV保存中 ({len(all_stop_times)} 行)...")  
    df = pd.DataFrame(all_stop_times)  
    df = df.drop_duplicates()  
    df.to_csv(f"{DATA_DIR}/stop_times.txt", index=False)  
    print("🎉 全路線のデータ構築が完了しました！")  
  
if __name__ == "__main__":  
    fetch_all_data()  
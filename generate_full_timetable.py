import pandas as pd  
import json  
import math  
import os  
from datetime import datetime, timedelta  
  
DATA_DIR = "data"  
INPUT_JSON = f"{DATA_DIR}/stations_kanto.json"  
OUTPUT_TXT = f"{DATA_DIR}/stop_times.txt"  
  
START_HOUR = 5  
END_HOUR = 25   
INTERVAL_MINUTES = 12   
TRAIN_SPEED_KMH = 45   
  
def haversine(lat1, lon1, lat2, lon2):  
    R = 6371  
    phi1, phi2 = math.radians(lat1), math.radians(lat2)  
    dphi = math.radians(lat2 - lat1)  
    dlambda = math.radians(lon2 - lon1)  
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2  
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))  
    return R * c  
  
def generate_full_data():  
    print("🚀 関東全路線の時刻表データを生成します...")  
  
    if not os.path.exists(INPUT_JSON):  
        print(f"❌ {INPUT_JSON} が見つかりません。")  
        return  
  
    with open(INPUT_JSON, "r", encoding="utf-8") as f:  
        stations = json.load(f)  
      
    lines = {}  
    for s in stations:  
        line_name = s["l"]  
        if line_name not in lines:  
            lines[line_name] = []  
        lines[line_name].append(s)  
  
    all_stop_times = []  
      
    for line_name, st_list in lines.items():  
        if len(st_list) < 2: continue  
          
        # 座標辞書  
        coords = {s['n']: (s.get('lat',0), s.get('lon',0)) for s in st_list}  
  
        # A: 下り  
        current_time = datetime(2000, 1, 1, START_HOUR, 0)  
        end_time = datetime(2000, 1, 1, 0, 0) + timedelta(hours=END_HOUR)  
          
        while current_time < end_time:  
            trip_id = f"{line_name}_D_{current_time.strftime('%H%M')}"  
            train_time = current_time  
              
            for i, s in enumerate(st_list):  
                travel_min = 0  
                if i > 0:  
                    prev = st_list[i-1]  
                    dist = haversine(prev.get('lat',0), prev.get('lon',0), s.get('lat',0), s.get('lon',0))  
                    travel_min = max(1, round((dist / TRAIN_SPEED_KMH) * 60))  
                    train_time += timedelta(minutes=travel_min)  
                  
                day_diff = (train_time.date() - datetime(2000, 1, 1).date()).days  
                h = train_time.hour + (24 * day_diff)  
                # バグ修正: 秒まで含めない、またはコロンを確実に  
                time_str = f"{h:02d}:{train_time.minute:02d}:00"  
                  
                all_stop_times.append({  
                    "trip_id": trip_id, "stop_id": s["n"],   
                    "arrival_time": time_str, "departure_time": time_str, "stop_sequence": i + 1  
                })  
            current_time += timedelta(minutes=INTERVAL_MINUTES)  
  
        # B: 上り  
        current_time = datetime(2000, 1, 1, START_HOUR, 0)  
        st_list_rev = st_list[::-1]  
          
        while current_time < end_time:  
            trip_id = f"{line_name}_U_{current_time.strftime('%H%M')}"  
            train_time = current_time  
              
            for i, s in enumerate(st_list_rev):  
                travel_min = 0  
                if i > 0:  
                    prev = st_list_rev[i-1]  
                    dist = haversine(prev.get('lat',0), prev.get('lon',0), s.get('lat',0), s.get('lon',0))  
                    travel_min = max(1, round((dist / TRAIN_SPEED_KMH) * 60))  
                    train_time += timedelta(minutes=travel_min)  
                  
                day_diff = (train_time.date() - datetime(2000, 1, 1).date()).days  
                h = train_time.hour + (24 * day_diff)  
                time_str = f"{h:02d}:{train_time.minute:02d}:00"  
                  
                all_stop_times.append({  
                    "trip_id": trip_id, "stop_id": s["n"],  
                    "arrival_time": time_str, "departure_time": time_str, "stop_sequence": i + 1  
                })  
            current_time += timedelta(minutes=INTERVAL_MINUTES)  
  
    print(f"💾 CSV保存中 ({len(all_stop_times)} 行)...")  
    df = pd.DataFrame(all_stop_times)  
    df.to_csv(OUTPUT_TXT, index=False)  
    print("🎉 完了！")  
  
if __name__ == "__main__":  
    generate_full_data()  
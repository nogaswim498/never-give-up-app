import os  
import pandas as pd  
from datetime import datetime, timedelta  
  
# 保存先ディレクトリ  
DATA_DIR = "data"  
os.makedirs(DATA_DIR, exist_ok=True)  
  
# --- 1. stops.txt (駅情報) ---  
# 渋谷を中心とした、東横線・田園都市線・JRの主要駅  
stops = [  
    # 起点  
    {"stop_id": "Shibuya", "stop_name": "渋谷", "stop_lat": 35.6580, "stop_lon": 139.7016},  
      
    # 東横線方面 (渋谷 -> 横浜)  
    {"stop_id": "Nakameguro", "stop_name": "中目黒", "stop_lat": 35.6442, "stop_lon": 139.6989},  
    {"stop_id": "Jiyugaoka", "stop_name": "自由が丘", "stop_lat": 35.6072, "stop_lon": 139.6687},  
    {"stop_id": "Musashi-Kosugi", "stop_name": "武蔵小杉", "stop_lat": 35.5768, "stop_lon": 139.6596}, # 重要拠点  
    {"stop_id": "Hiyoshi", "stop_name": "日吉", "stop_lat": 35.5544, "stop_lon": 139.6469},  
    {"stop_id": "Kikuna", "stop_name": "菊名", "stop_lat": 35.5097, "stop_lon": 139.6304}, # 終電によくある止まり駅  
    {"stop_id": "Yokohama", "stop_name": "横浜", "stop_lat": 35.4657, "stop_lon": 139.6223}, # 目的地  
    {"stop_id": "Motomachi", "stop_name": "元町・中華街", "stop_lat": 35.4429, "stop_lon": 139.6498},  
  
    # 田園都市線方面 (渋谷 -> 中央林間)  
    {"stop_id": "Sangen-Jaya", "stop_name": "三軒茶屋", "stop_lat": 35.6433, "stop_lon": 139.6702},  
    {"stop_id": "Futako-Tamagawa", "stop_name": "二子玉川", "stop_lat": 35.6116, "stop_lon": 139.6265},  
    {"stop_id": "Mizonokuchi", "stop_name": "溝の口", "stop_lat": 35.5999, "stop_lon": 139.6105},  
    {"stop_id": "Saginuma", "stop_name": "鷺沼", "stop_lat": 35.5794, "stop_lon": 139.5731}, # 車庫があるため終電候補  
    {"stop_id": "Nagatsuta", "stop_name": "長津田", "stop_lat": 35.5317, "stop_lon": 139.4950},  
    {"stop_id": "Chuo-Rinkan", "stop_name": "中央林間", "stop_lat": 35.5074, "stop_lon": 139.4443},  
]  
pd.DataFrame(stops).to_csv(f"{DATA_DIR}/stops.txt", index=False)  
print("✅ stops.txt generated (Shibuya scenario).")  
  
# --- 2. stop_times.txt (時刻表) ---  
stop_times = []  
  
def add_trip(trip_id, route_stops, start_time_str, duration_minutes_list):  
    current_time = datetime.strptime(start_time_str, "%H:%M:%S")  
    for i, stop_id in enumerate(route_stops):  
        time_str = current_time.strftime("%H:%M:%S")  
        stop_times.append({  
            "trip_id": trip_id,  
            "stop_id": stop_id,  
            "arrival_time": time_str,  
            "departure_time": time_str, # 簡易化のため発着同刻  
            "stop_sequence": i + 1  
        })  
        if i < len(duration_minutes_list):  
            current_time += timedelta(minutes=duration_minutes_list[i])  
  
# ==========================================  
# 終電間際のダイヤ設定 (現在時刻は 24:40 想定)  
# ==========================================  
  
# 1. 【東横線】 横浜まで行く最終電車 (24:20発) -> もう行ってしまった！  
add_trip("Toyoko_Last_Yokohama",  
         ["Shibuya", "Nakameguro", "Jiyugaoka", "Musashi-Kosugi", "Kikuna", "Yokohama"],  
         "00:20:00", [3, 5, 5, 8, 6]) # 24:47着  
  
# 2. 【東横線】 菊名止まりの最終 (24:42発) -> ★これに乗れる！(2分後)  
# 横浜までは行けないが、菊名までは行ける  
add_trip("Toyoko_Last_Kikuna",  
         ["Shibuya", "Nakameguro", "Jiyugaoka", "Musashi-Kosugi", "Kikuna"],  
         "00:42:00", [3, 5, 5, 8]) # 01:03 菊名着  
  
# 3. 【東横線】 武蔵小杉止まりの最終 (24:55発) -> ★余裕で乗れるが距離は短い  
add_trip("Toyoko_Last_Kosugi",  
         ["Shibuya", "Nakameguro", "Jiyugaoka", "Musashi-Kosugi"],  
         "00:55:00", [3, 5, 5])  
  
# 4. 【田園都市線】 長津田まで行く最終 (24:15発) -> もう行ってしまった  
add_trip("Denentoshi_Last_Nagatsuta",  
         ["Shibuya", "Sangen-Jaya", "Futako-Tamagawa", "Mizonokuchi", "Saginuma", "Nagatsuta"],  
         "00:15:00", [5, 10, 5, 7, 10])  
  
# 5. 【田園都市線】 鷺沼止まりの最終 (24:45発) -> ★これに乗れる！  
add_trip("Denentoshi_Last_Saginuma",  
         ["Shibuya", "Sangen-Jaya", "Futako-Tamagawa", "Mizonokuchi", "Saginuma"],  
         "00:45:00", [5, 10, 5, 7]) # 01:12 鷺沼着  
  
pd.DataFrame(stop_times).to_csv(f"{DATA_DIR}/stop_times.txt", index=False)  
print("✅ stop_times.txt generated (Shibuya scenario).")  
  
print("\n🎉 リアルな渋谷終電データを作成しました！")  
print("想定シナリオ: 24:40現在、渋谷にいる。横浜に帰りたいが直通は終わっている状況。")  
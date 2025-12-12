import os  
import pandas as pd  
from datetime import datetime, timedelta  
  
DATA_DIR = "data"  
os.makedirs(DATA_DIR, exist_ok=True)  
  
# === 1. 主要駅データ ===  
stations = [  
    # 山手線・主要ターミナル  
    {"id": "Tokyo", "name": "東京", "lat": 35.6812, "lon": 139.7671},  
    {"id": "Shinagawa", "name": "品川", "lat": 35.6284, "lon": 139.7387},  
    {"id": "Shibuya", "name": "渋谷", "lat": 35.6580, "lon": 139.7016},  
    {"id": "Shinjuku", "name": "新宿", "lat": 35.6895, "lon": 139.7004},  
    {"id": "Ikebukuro", "name": "池袋", "lat": 35.7295, "lon": 139.7109},  
    {"id": "Ueno", "name": "上野", "lat": 35.7141, "lon": 139.7774},  
    {"id": "Akihabara", "name": "秋葉原", "lat": 35.6983, "lon": 139.7730},  
    {"id": "Shinbashi", "name": "新橋", "lat": 35.6664, "lon": 139.7583},  
  
    # 東海道線・京浜東北線・横須賀線 (神奈川方面)  
    {"id": "Kawasaki", "name": "川崎", "lat": 35.5313, "lon": 139.6974},  
    {"id": "Yokohama", "name": "横浜", "lat": 35.4657, "lon": 139.6223},  
    {"id": "Ofuna", "name": "大船", "lat": 35.3541, "lon": 139.5313},  
    {"id": "Fujisawa", "name": "藤沢", "lat": 35.3389, "lon": 139.4883},  
    {"id": "Odawara", "name": "小田原", "lat": 35.2562, "lon": 139.1553},  
    {"id": "Hiratsuka", "name": "平塚", "lat": 35.3274, "lon": 139.3490},  
  
    # 中央線 (西東京方面)  
    {"id": "Nakano", "name": "中野", "lat": 35.7058, "lon": 139.6658},  
    {"id": "Mitaka", "name": "三鷹", "lat": 35.7027, "lon": 139.5607},  
    {"id": "Tachikawa", "name": "立川", "lat": 35.6994, "lon": 139.4130},  
    {"id": "Hachioji", "name": "八王子", "lat": 35.6554, "lon": 139.3389},  
    {"id": "Takao", "name": "高尾", "lat": 35.6420, "lon": 139.2822},  
  
    # 埼京線・高崎線・宇都宮線 (埼玉方面)  
    {"id": "Akabane", "name": "赤羽", "lat": 35.7776, "lon": 139.7210},  
    {"id": "Urawa", "name": "浦和", "lat": 35.8570, "lon": 139.6573},  
    {"id": "Omiya", "name": "大宮", "lat": 35.9063, "lon": 139.6240},  
    {"id": "Kumagaya", "name": "熊谷", "lat": 36.1396, "lon": 139.3895},  
    {"id": "Takasaki", "name": "高崎", "lat": 36.3224, "lon": 139.0127},  
  
    # 総武線・京葉線 (千葉方面)  
    {"id": "Funabashi", "name": "船橋", "lat": 35.7017, "lon": 139.9852},  
    {"id": "Tsudanuma", "name": "津田沼", "lat": 35.6914, "lon": 140.0205},  
    {"id": "Chiba", "name": "千葉", "lat": 35.6133, "lon": 140.1135},  
    {"id": "Soga", "name": "蘇我", "lat": 35.5818, "lon": 140.1307},  
  
    # 私鉄主要駅  
    {"id": "Jiyugaoka", "name": "自由が丘", "lat": 35.6072, "lon": 139.6687},  
    {"id": "Musashi-Kosugi", "name": "武蔵小杉", "lat": 35.5768, "lon": 139.6596},  
    {"id": "Kikuna", "name": "菊名", "lat": 35.5097, "lon": 139.6304},  
    {"id": "Machida", "name": "町田", "lat": 35.5420, "lon": 139.4455},  
    {"id": "Hon-Atsugi", "name": "本厚木", "lat": 35.4392, "lon": 139.3636},  
    {"id": "Chofu", "name": "調布", "lat": 35.6521, "lon": 139.5442},  
    {"id": "Hashimoto", "name": "橋本", "lat": 35.5948, "lon": 139.3450}  
]  
  
df_stops = pd.DataFrame([{  
    "stop_id": s["id"],   
    "stop_name": s["name"],   
    "stop_lat": s["lat"],   
    "stop_lon": s["lon"]  
} for s in stations])  
df_stops.to_csv(f"{DATA_DIR}/stops.txt", index=False)  
print("✅ stops.txt updated.")  
  
# === 2. 路線・時刻表生成 ===  
stop_times = []  
  
def create_route(route_name, stop_list, start_times, interval_mins, travel_times):  
    for start_str in start_times:  
        # 修正: 24:xx を手動でパースして datetime オブジェクトを作る  
        h_val, m_val = map(int, start_str.split(':'))  
          
        # 計算用の基準日時 (2000/1/1 00:00:00)  
        base_time = datetime(2000, 1, 1)  
          
        # 時間を加算 (これで 24:15 は翌日の 00:15 になる)  
        current_time = base_time + timedelta(hours=h_val, minutes=m_val)  
          
        # 便ID  
        trip_id = f"{route_name}_{start_str.replace(':', '')}"  
          
        for i, stop_id in enumerate(stop_list):  
            # 24時越え表記へ戻すロジック (00:30 -> 24:30)  
            # データ上の日付が「翌日(1/2)」になっているか、時間が早朝(0~4時)なら深夜便扱い  
            day_diff = (current_time.date() - base_time.date()).days  
              
            output_h = current_time.hour  
            # 日付がまたがっている、または深夜帯なら24を加算して表示  
            if day_diff > 0 or current_time.hour < 5:  
                output_h += 24  
              
            time_str = f"{output_h:02d}:{current_time.minute:02d}:00"  
              
            stop_times.append({  
                "trip_id": trip_id,  
                "stop_id": stop_id,  
                "arrival_time": time_str,  
                "departure_time": time_str,  
                "stop_sequence": i + 1  
            })  
              
            if i < len(interval_mins):  
                current_time += timedelta(minutes=interval_mins[i])  
  
# --- ルート定義 ---  
  
# 1. 東海道線 (東京 -> 小田原・熱海方面)  
stops_tokaido = ["Tokyo", "Shinagawa", "Kawasaki", "Yokohama", "Ofuna", "Fujisawa", "Hiratsuka", "Odawara"]  
times_tokaido = [7, 9, 8, 15, 5, 6, 15]   
create_route("Tokaido", stops_tokaido, ["23:00", "23:20", "23:40"], times_tokaido, times_tokaido)  
create_route("Tokaido_Last", stops_tokaido[:-1], ["23:54"], times_tokaido[:-1], times_tokaido[:-1])  
  
# 2. 中央線 (東京/新宿 -> 高尾方面)  
stops_chuo = ["Tokyo", "Shinjuku", "Nakano", "Mitaka", "Tachikawa", "Hachioji", "Takao"]  
times_chuo = [14, 5, 8, 15, 10, 7]  
create_route("Chuo", stops_chuo, ["23:10", "23:30", "23:50"], times_chuo, times_chuo)  
create_route("Chuo_Last", stops_chuo[:5], ["24:15"], times_chuo[:4], times_chuo[:4])   
  
# 3. 埼京線/高崎線 (新宿/上野 -> 大宮方面)  
stops_saikyo = ["Shinjuku", "Ikebukuro", "Akabane", "Urawa", "Omiya", "Kumagaya"]  
times_saikyo = [6, 9, 10, 7, 25]  
create_route("Saikyo", stops_saikyo, ["23:15", "23:45"], times_saikyo, times_saikyo)  
create_route("Saikyo_Last", stops_saikyo[:5], ["24:05"], times_saikyo[:4], times_saikyo[:4])  
  
# 4. 総武線 (新宿/秋葉原 -> 千葉方面)  
stops_sobu = ["Shinjuku", "Akihabara", "Funabashi", "Tsudanuma", "Chiba"]  
times_sobu = [18, 25, 4, 10]  
create_route("Sobu", stops_sobu, ["23:20", "23:50"], times_sobu, times_sobu)  
create_route("Sobu_Last", stops_sobu[:4], ["24:20"], times_sobu[:3], times_sobu[:3])  
  
# 5. 東急東横線 (渋谷 -> 横浜方面)  
stops_toyoko = ["Shibuya", "Jiyugaoka", "Musashi-Kosugi", "Kikuna", "Yokohama"]  
times_toyoko = [10, 5, 8, 6]  
create_route("Toyoko", stops_toyoko, ["23:30", "23:50", "24:10"], times_toyoko, times_toyoko)  
create_route("Toyoko_Last", stops_toyoko[:4], ["24:42"], times_toyoko[:3], times_toyoko[:3])  
  
pd.DataFrame(stop_times).to_csv(f"{DATA_DIR}/stop_times.txt", index=False)  
print("✅ stop_times.txt updated.")  
print("首都圏主要路線の終電ダイヤ(擬似)を生成しました！")  
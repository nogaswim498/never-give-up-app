import os  
import pandas as pd  
from datetime import datetime, timedelta  
  
DATA_DIR = "data"  
os.makedirs(DATA_DIR, exist_ok=True)  
  
print("ℹ️  このスクリプトは時刻表データ(stop_times.txt)のみを生成します。")  
print("ℹ️  駅データ(stops.txt)は fetch_stations.py で生成したものを使用します。")  
  
# === 時刻表データ生成 ===  
stop_times = []  
  
def create_route(route_name, stop_list, start_times, interval_mins):  
    for start_str in start_times:  
        h_val, m_val = map(int, start_str.split(':'))  
        base_time = datetime(2000, 1, 1)  
        current_time = base_time + timedelta(hours=h_val, minutes=m_val)  
        trip_id = f"{route_name}_{start_str.replace(':', '')}"  
          
        for i, stop_id in enumerate(stop_list):  
            day_diff = (current_time.date() - base_time.date()).days  
            output_h = current_time.hour  
            # 深夜判定  
            if day_diff > 0 or current_time.hour < 5: output_h += 24  
              
            time_str = f"{output_h:02d}:{current_time.minute:02d}:00"  
              
            stop_times.append({  
                "trip_id": trip_id,   
                "stop_id": stop_id, # 日本語ID  
                "arrival_time": time_str,   
                "departure_time": time_str,   
                "stop_sequence": i + 1  
            })  
            if i < len(interval_mins):  
                current_time += timedelta(minutes=interval_mins[i])  
  
# --- ルート定義 (主要路線のみ) ---  
# ※ここにある駅以外を検索すると「ルートなし（タクシーのみ）」になりますが、エラーにはなりません。  
  
# 東海道線  
stops_tokaido = ["東京", "品川", "川崎", "横浜", "大船", "藤沢", "辻堂", "茅ケ崎", "平塚", "小田原"]  
times_tokaido = [7, 9, 8, 15, 5, 4, 4, 5, 15]  
create_route("Tokaido", stops_tokaido, ["23:00", "23:20", "23:40"], times_tokaido)  
create_route("Tokaido_Last", stops_tokaido[:-1], ["23:54"], times_tokaido[:-1])  
  
# 東横線  
stops_toyoko = ["渋谷", "自由が丘", "武蔵小杉", "日吉", "菊名", "横浜"]  
times_toyoko = [10, 5, 4, 6, 6]  
create_route("Toyoko", stops_toyoko, ["23:30", "23:50", "24:10"], times_toyoko)  
create_route("Toyoko_Last", stops_toyoko[:-1], ["24:42"], times_toyoko[:-1])  
  
# 田園都市線  
stops_denen = ["渋谷", "二子玉川", "溝の口", "鷺沼", "あざみ野", "青葉台", "長津田", "町田", "中央林間"]  
times_denen = [13, 5, 7, 3, 4, 5, 7, 8]  
create_route("Denen", stops_denen, ["23:30", "23:55", "24:15"], times_denen)  
create_route("Denen_Last", stops_denen[:4], ["24:45"], times_denen[:3])  
  
# 小田急線  
stops_odakyu = ["新宿", "登戸", "新百合ヶ丘", "町田", "相模大野", "海老名", "本厚木", "小田原"]  
times_odakyu = [18, 9, 10, 4, 10, 5, 25]  
create_route("Odakyu", stops_odakyu, ["23:30", "23:55", "24:20"], times_odakyu)  
create_route("Odakyu_Last", stops_odakyu[:-1], ["24:40"], times_odakyu[:-1])  
  
# 京王線  
stops_keio = ["新宿", "調布", "府中", "聖蹟桜ヶ丘", "八王子", "高尾"]  
times_keio = [15, 6, 5, 12, 7]  
create_route("Keio", stops_keio, ["23:40", "24:00", "24:20"], times_keio)  
create_route("Keio_Hashimoto", ["新宿", "調布", "橋本"], ["23:50", "24:15"], [15, 20])  
  
# 中央線  
stops_chuo = ["東京", "新宿", "中野", "三鷹", "吉祥寺", "立川", "八王子", "高尾"]  
times_chuo = [14, 5, 8, 2, 12, 10, 7]  
create_route("Chuo", stops_chuo, ["23:10", "23:30", "23:50"], times_chuo)  
create_route("Chuo_Last", stops_chuo[:6], ["24:15"], times_chuo[:5])  
  
# 保存 (stops.txt は上書きしない！)  
pd.DataFrame(stop_times).to_csv(f"{DATA_DIR}/stop_times.txt", index=False)  
print("✅ stop_times.txt updated. (時刻表データのみ更新しました)")  
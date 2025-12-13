import os  
import pandas as pd  
from datetime import datetime, timedelta  
  
DATA_DIR = "data"  
os.makedirs(DATA_DIR, exist_ok=True)  
  
# === 1. 大規模駅データ (関東主要路線) ===  
stations = [  
    # 山手線  
    {"id":"Tokyo","name":"東京","lat":35.6812,"lon":139.7671}, {"id":"Shinagawa","name":"品川","lat":35.6284,"lon":139.7387},  
    {"id":"Shibuya","name":"渋谷","lat":35.6580,"lon":139.7016}, {"id":"Shinjuku","name":"新宿","lat":35.6895,"lon":139.7004},  
    {"id":"Ikebukuro","name":"池袋","lat":35.7295,"lon":139.7109}, {"id":"Ueno","name":"上野","lat":35.7141,"lon":139.7774},  
    # 東海道・横須賀・湘南新宿  
    {"id":"Kawasaki","name":"川崎","lat":35.5313,"lon":139.6974}, {"id":"Yokohama","name":"横浜","lat":35.4657,"lon":139.6223},  
    {"id":"Ofuna","name":"大船","lat":35.3541,"lon":139.5313}, {"id":"Fujisawa","name":"藤沢","lat":35.3389,"lon":139.4883},  
    {"id":"Tsujido","name":"辻堂","lat":35.3368,"lon":139.4471}, {"id":"Chigasaki","name":"茅ケ崎","lat":35.3304,"lon":139.4067},  
    {"id":"Hiratsuka","name":"平塚","lat":35.3274,"lon":139.3490}, {"id":"Odawara","name":"小田原","lat":35.2562,"lon":139.1553},  
    # 中央線  
    {"id":"Nakano","name":"中野","lat":35.7058,"lon":139.6658}, {"id":"Mitaka","name":"三鷹","lat":35.7027,"lon":139.5607},  
    {"id":"Kichijoji","name":"吉祥寺","lat":35.7031,"lon":139.5798}, {"id":"Tachikawa","name":"立川","lat":35.6994,"lon":139.4130},  
    {"id":"Hachioji","name":"八王子","lat":35.6554,"lon":139.3389}, {"id":"Takao","name":"高尾","lat":35.6420,"lon":139.2822},  
    # 東急線 (東横・田園都市)  
    {"id":"Musashi-Kosugi","name":"武蔵小杉","lat":35.5768,"lon":139.6596}, {"id":"Hiyoshi","name":"日吉","lat":35.5544,"lon":139.6469},  
    {"id":"Kikuna","name":"菊名","lat":35.5097,"lon":139.6304}, {"id":"Jiyugaoka","name":"自由が丘","lat":35.6072,"lon":139.6687},  
    {"id":"Futako-Tamagawa","name":"二子玉川","lat":35.6116,"lon":139.6265}, {"id":"Mizonokuchi","name":"溝の口","lat":35.5999,"lon":139.6105},  
    {"id":"Saginuma","name":"鷺沼","lat":35.5794,"lon":139.5731}, {"id":"Azamino","name":"あざみ野","lat":35.5684,"lon":139.5534},  
    {"id":"Aobadai","name":"青葉台","lat":35.5428,"lon":139.5173}, {"id":"Nagatsuta","name":"長津田","lat":35.5317,"lon":139.4950},  
    {"id":"Machida","name":"町田","lat":35.5420,"lon":139.4455}, {"id":"Chuo-Rinkan","name":"中央林間","lat":35.5074,"lon":139.4443},  
    # 小田急線  
    {"id":"Noborito","name":"登戸","lat":35.6209,"lon":139.5699}, {"id":"Shin-Yurigaoka","name":"新百合ヶ丘","lat":35.6035,"lon":139.5074},  
    {"id":"Sagami-Ono","name":"相模大野","lat":35.5323,"lon":139.4377}, {"id":"Ebina","name":"海老名","lat":35.4526,"lon":139.3907},  
    {"id":"Hon-Atsugi","name":"本厚木","lat":35.4392,"lon":139.3636},  
    # 京王線  
    {"id":"Chofu","name":"調布","lat":35.6521,"lon":139.5442}, {"id":"Fuchu","name":"府中","lat":35.6721,"lon":139.4804},  
    {"id":"Seiseki-Sakuragaoka","name":"聖蹟桜ヶ丘","lat":35.6508,"lon":139.4470}, {"id":"Hashimoto","name":"橋本","lat":35.5948,"lon":139.3450},  
    # 相鉄線  
    {"id":"Futamatagawa","name":"二俣川","lat":35.4633,"lon":139.5342}, {"id":"Yamato","name":"大和","lat":35.4697,"lon":139.4623},  
    # 埼玉方面 (埼京・京浜東北)  
    {"id":"Akabane","name":"赤羽","lat":35.7776,"lon":139.7210}, {"id":"Urawa","name":"浦和","lat":35.8570,"lon":139.6573},  
    {"id":"Omiya","name":"大宮","lat":35.9063,"lon":139.6240}, {"id":"Kawaguchi","name":"川口","lat":35.8021,"lon":139.7175},  
    # 千葉方面  
    {"id":"Funabashi","name":"船橋","lat":35.7017,"lon":139.9852}, {"id":"Tsudanuma","name":"津田沼","lat":35.6914,"lon":140.0205},  
    {"id":"Chiba","name":"千葉","lat":35.6133,"lon":140.1135}, {"id":"Kashiwa","name":"柏","lat":35.8622,"lon":139.9709}  
]  
  
# データフレーム保存  
df_stops = pd.DataFrame([{ "stop_id": s["id"], "stop_name": s["name"], "stop_lat": s["lat"], "stop_lon": s["lon"] } for s in stations])  
df_stops.to_csv(f"{DATA_DIR}/stops.txt", index=False)  
print("✅ stops.txt updated.")  
  
# === 2. 路線生成 (さらに増やす) ===  
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
            if day_diff > 0 or current_time.hour < 5: output_h += 24  
              
            time_str = f"{output_h:02d}:{current_time.minute:02d}:00"  
            stop_times.append({  
                "trip_id": trip_id, "stop_id": stop_id, "arrival_time": time_str, "departure_time": time_str, "stop_sequence": i + 1  
            })  
            if i < len(interval_mins):  
                current_time += timedelta(minutes=interval_mins[i])  
  
# --- ルート定義 (23時〜25時を中心に拡充) ---  
  
# 東海道線  
stops_tokaido = ["Tokyo", "Shinagawa", "Kawasaki", "Yokohama", "Ofuna", "Fujisawa", "Tsujido", "Chigasaki", "Hiratsuka", "Odawara"]  
times_tokaido = [7, 9, 8, 15, 5, 4, 4, 5, 15]  
create_route("Tokaido", stops_tokaido, ["23:00", "23:20", "23:40"], times_tokaido)  
create_route("Tokaido_Last", stops_tokaido[:-1], ["23:54"], times_tokaido[:-1]) # 平塚止まり  
  
# 東横線  
stops_toyoko = ["Shibuya", "Jiyugaoka", "Musashi-Kosugi", "Hiyoshi", "Kikuna", "Yokohama"]  
times_toyoko = [10, 5, 4, 6, 6]  
create_route("Toyoko", stops_toyoko, ["23:30", "23:50", "24:10"], times_toyoko)  
create_route("Toyoko_Last", stops_toyoko[:-1], ["24:42"], times_toyoko[:-1]) # 菊名止まり  
  
# 田園都市線  
stops_denen = ["Shibuya", "Futako-Tamagawa", "Mizonokuchi", "Saginuma", "Azamino", "Aobadai", "Nagatsuta", "Machida", "Chuo-Rinkan"]  
times_denen = [13, 5, 7, 3, 4, 5, 7, 8]  
create_route("Denen", stops_denen, ["23:30", "23:55", "24:15"], times_denen)  
create_route("Denen_Last", stops_denen[:4], ["24:45"], times_denen[:3]) # 鷺沼止まり  
  
# 小田急線  
stops_odakyu = ["Shinjuku", "Noborito", "Shin-Yurigaoka", "Machida", "Sagami-Ono", "Ebina", "Hon-Atsugi", "Odawara"]  
times_odakyu = [18, 9, 10, 4, 10, 5, 25]  
create_route("Odakyu", stops_odakyu, ["23:30", "23:55", "24:20"], times_odakyu)  
create_route("Odakyu_Last", stops_odakyu[:-1], ["24:40"], times_odakyu[:-1]) # 本厚木止まり  
  
# 京王線  
stops_keio = ["Shinjuku", "Chofu", "Fuchu", "Seiseki-Sakuragaoka", "Hachioji", "Takao"]  
times_keio = [15, 6, 5, 12, 7]  
create_route("Keio", stops_keio, ["23:40", "24:00", "24:20"], times_keio)  
create_route("Keio_Hashimoto", ["Shinjuku", "Chofu", "Hashimoto"], ["23:50", "24:15"], [15, 20])  
  
# 相鉄線 (横浜発)  
stops_sotetsu = ["Yokohama", "Futamatagawa", "Yamato", "Ebina"]  
times_sotetsu = [12, 10, 10]  
create_route("Sotetsu", stops_sotetsu, ["23:30", "24:00", "24:25"], times_sotetsu)  
  
pd.DataFrame(stop_times).to_csv(f"{DATA_DIR}/stop_times.txt", index=False)  
print("✅ stop_times.txt updated.")  
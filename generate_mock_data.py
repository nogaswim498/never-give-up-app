import os  
import pandas as pd  
import json  
from datetime import datetime, timedelta  
  
DATA_DIR = "data"  
os.makedirs(DATA_DIR, exist_ok=True)  
  
# === 1. マスター駅データ (漢字, かな, 緯度, 経度, 路線表示用) ===  
# ここにある駅だけが検索候補に出ます  
stations = [  
    # --- 山手線・都心 ---  
    {"id":"新宿","n":"新宿","k":"しんじゅく","l":"JR/小田急/京王","lat":35.6895,"lon":139.7004},  
    {"id":"渋谷","n":"渋谷","k":"しぶや","l":"JR/東急/京王","lat":35.6580,"lon":139.7016},  
    {"id":"池袋","n":"池袋","k":"いけぶくろ","l":"JR/西武/東武","lat":35.7295,"lon":139.7109},  
    {"id":"東京","n":"東京","k":"とうきょう","l":"JR/メトロ","lat":35.6812,"lon":139.7671},  
    {"id":"品川","n":"品川","k":"しながわ","l":"JR/京急","lat":35.6284,"lon":139.7387},  
    {"id":"上野","n":"上野","k":"うえの","l":"JR/メトロ","lat":35.7141,"lon":139.7774},  
    {"id":"秋葉原","n":"秋葉原","k":"あきはばら","l":"JR/つくば","lat":35.6983,"lon":139.7730},  
    {"id":"新橋","n":"新橋","k":"しんばし","l":"JR/メトロ","lat":35.6664,"lon":139.7583},  
      
    # --- 東海道・横須賀・湘南新宿 ---  
    {"id":"川崎","n":"川崎","k":"かわさき","l":"JR/京急","lat":35.5313,"lon":139.6974},  
    {"id":"横浜","n":"横浜","k":"よこはま","l":"JR/東急/相鉄","lat":35.4657,"lon":139.6223},  
    {"id":"大船","n":"大船","k":"おおふな","l":"JR","lat":35.3541,"lon":139.5313},  
    {"id":"藤沢","n":"藤沢","k":"ふじさわ","l":"JR/小田急","lat":35.3389,"lon":139.4883},  
    {"id":"辻堂","n":"辻堂","k":"つじどう","l":"JR","lat":35.3368,"lon":139.4471},  
    {"id":"茅ケ崎","n":"茅ケ崎","k":"ちがさき","l":"JR","lat":35.3304,"lon":139.4067},  
    {"id":"平塚","n":"平塚","k":"ひらつか","l":"JR","lat":35.3274,"lon":139.3490},  
    {"id":"小田原","n":"小田原","k":"おだわら","l":"JR/小田急","lat":35.2562,"lon":139.1553},  
      
    # --- 中央線 ---  
    {"id":"中野","n":"中野","k":"なかの","l":"JR/メトロ","lat":35.7058,"lon":139.6658},  
    {"id":"三鷹","n":"三鷹","k":"みたか","l":"JR","lat":35.7027,"lon":139.5607},  
    {"id":"吉祥寺","n":"吉祥寺","k":"きちじょうじ","l":"JR/京王","lat":35.7031,"lon":139.5798},  
    {"id":"立川","n":"立川","k":"たちかわ","l":"JR","lat":35.6994,"lon":139.4130},  
    {"id":"八王子","n":"八王子","k":"はちおうじ","l":"JR","lat":35.6554,"lon":139.3389},  
    {"id":"高尾","n":"高尾","k":"たかお","l":"JR/京王","lat":35.6420,"lon":139.2822},  
      
    # --- 東急線 ---  
    {"id":"武蔵小杉","n":"武蔵小杉","k":"むさしこすぎ","l":"JR/東急","lat":35.5768,"lon":139.6596},  
    {"id":"日吉","n":"日吉","k":"ひよし","l":"東急","lat":35.5544,"lon":139.6469},  
    {"id":"菊名","n":"菊名","k":"きくな","l":"東急/JR","lat":35.5097,"lon":139.6304},  
    {"id":"自由が丘","n":"自由が丘","k":"じゆうがおか","l":"東急","lat":35.6072,"lon":139.6687},  
    {"id":"二子玉川","n":"二子玉川","k":"ふたこたまがわ","l":"東急","lat":35.6116,"lon":139.6265},  
    {"id":"溝の口","n":"溝の口","k":"みぞのくち","l":"東急/JR","lat":35.5999,"lon":139.6105},  
    {"id":"鷺沼","n":"鷺沼","k":"さぎぬま","l":"東急","lat":35.5794,"lon":139.5731},  
    {"id":"あざみ野","n":"あざみ野","k":"あざみの","l":"東急","lat":35.5684,"lon":139.5534},  
    {"id":"青葉台","n":"青葉台","k":"あおばだい","l":"東急","lat":35.5428,"lon":139.5173},  
    {"id":"長津田","n":"長津田","k":"ながつた","l":"東急/JR","lat":35.5317,"lon":139.4950},  
    {"id":"町田","n":"町田","k":"まちだ","l":"JR/小田急","lat":35.5420,"lon":139.4455},  
    {"id":"中央林間","n":"中央林間","k":"ちゅうおうりんかん","l":"東急/小田急","lat":35.5074,"lon":139.4443},  
      
    # --- 小田急線 ---  
    {"id":"登戸","n":"登戸","k":"のぼりと","l":"小田急/JR","lat":35.6209,"lon":139.5699},  
    {"id":"新百合ヶ丘","n":"新百合ヶ丘","k":"しんゆりがおか","l":"小田急","lat":35.6035,"lon":139.5074},  
    {"id":"相模大野","n":"相模大野","k":"さがみおおの","l":"小田急","lat":35.5323,"lon":139.4377},  
    {"id":"海老名","n":"海老名","k":"えびな","l":"小田急/相鉄/JR","lat":35.4526,"lon":139.3907},  
    {"id":"本厚木","n":"本厚木","k":"ほんあつぎ","l":"小田急","lat":35.4392,"lon":139.3636},  
      
    # --- 京王線 ---  
    {"id":"調布","n":"調布","k":"ちょうふ","l":"京王","lat":35.6521,"lon":139.5442},  
    {"id":"府中","n":"府中","k":"ふちゅう","l":"京王","lat":35.6721,"lon":139.4804},  
    {"id":"聖蹟桜ヶ丘","n":"聖蹟桜ヶ丘","k":"せいせきさくらがおか","l":"京王","lat":35.6508,"lon":139.4470},  
    {"id":"橋本","n":"橋本","k":"はしもと","l":"京王/JR","lat":35.5948,"lon":139.3450},  
  
    # --- 埼京・京浜東北 (埼玉方面) ---  
    {"id":"赤羽","n":"赤羽","k":"あかばね","l":"JR","lat":35.7776,"lon":139.7210},  
    {"id":"浦和","n":"浦和","k":"うらわ","l":"JR","lat":35.8570,"lon":139.6573},  
    {"id":"大宮","n":"大宮","k":"おおみや","l":"JR","lat":35.9063,"lon":139.6240},  
    {"id":"川口","n":"川口","k":"かわぐち","l":"JR","lat":35.8021,"lon":139.7175},  
  
    # --- 千葉方面 ---  
    {"id":"船橋","n":"船橋","k":"ふなばし","l":"JR/東武","lat":35.7017,"lon":139.9852},  
    {"id":"津田沼","n":"津田沼","k":"つだぬま","l":"JR","lat":35.6914,"lon":140.0205},  
    {"id":"千葉","n":"千葉","k":"ちば","l":"JR","lat":35.6133,"lon":140.1135},  
    {"id":"柏","n":"柏","k":"かしわ","l":"JR/東武","lat":35.8622,"lon":139.9709}  
]  
  
# 1. バックエンド用 (stops.txt)  
df_stops = pd.DataFrame([{ "stop_id": s["id"], "stop_name": s["n"], "stop_lat": s["lat"], "stop_lon": s["lon"] } for s in stations])  
df_stops.to_csv(f"{DATA_DIR}/stops.txt", index=False)  
print("✅ stops.txt updated.")  
  
# 2. フロントエンド用 (stations_kanto.json)  
# ここに「ひらがな(k)」を含めることでサジェストに対応  
with open(f"{DATA_DIR}/stations_kanto.json", "w", encoding="utf-8") as f:  
    json.dump(stations, f, ensure_ascii=False, separators=(',', ':'))  
print("✅ stations_kanto.json updated.")  
  
  
# === 3. 時刻表データ生成 (IDを日本語名に統一) ===  
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
  
# --- ルート定義 (23時〜25時中心) ---  
  
# 東海道線  
stops_tokaido = ["東京", "品川", "川崎", "横浜", "大船", "藤沢", "辻堂", "茅ケ崎", "平塚", "小田原"]  
times_tokaido = [7, 9, 8, 15, 5, 4, 4, 5, 15]  
create_route("Tokaido", stops_tokaido, ["23:00", "23:20", "23:40"], times_tokaido)  
create_route("Tokaido_Last", stops_tokaido[:-1], ["23:54"], times_tokaido[:-1]) # 平塚止まり  
  
# 東横線  
stops_toyoko = ["渋谷", "自由が丘", "武蔵小杉", "日吉", "菊名", "横浜"]  
times_toyoko = [10, 5, 4, 6, 6]  
create_route("Toyoko", stops_toyoko, ["23:30", "23:50", "24:10"], times_toyoko)  
create_route("Toyoko_Last", stops_toyoko[:-1], ["24:42"], times_toyoko[:-1]) # 菊名止まり  
  
# 田園都市線  
stops_denen = ["渋谷", "二子玉川", "溝の口", "鷺沼", "あざみ野", "青葉台", "長津田", "町田", "中央林間"]  
times_denen = [13, 5, 7, 3, 4, 5, 7, 8]  
create_route("Denen", stops_denen, ["23:30", "23:55", "24:15"], times_denen)  
create_route("Denen_Last", stops_denen[:4], ["24:45"], times_denen[:3]) # 鷺沼止まり  
  
# 小田急線  
stops_odakyu = ["新宿", "登戸", "新百合ヶ丘", "町田", "相模大野", "海老名", "本厚木", "小田原"]  
times_odakyu = [18, 9, 10, 4, 10, 5, 25]  
create_route("Odakyu", stops_odakyu, ["23:30", "23:55", "24:20"], times_odakyu)  
create_route("Odakyu_Last", stops_odakyu[:-1], ["24:40"], times_odakyu[:-1]) # 本厚木止まり  
  
# 京王線  
stops_keio = ["新宿", "調布", "府中", "聖蹟桜ヶ丘", "八王子", "高尾"]  
times_keio = [15, 6, 5, 12, 7]  
create_route("Keio", stops_keio, ["23:40", "24:00", "24:20"], times_keio)  
create_route("Keio_Hashimoto", ["新宿", "調布", "橋本"], ["23:50", "24:15"], [15, 20])  
  
# 中央線  
stops_chuo = ["東京", "新宿", "中野", "三鷹", "吉祥寺", "立川", "八王子", "高尾"]  
times_chuo = [14, 5, 8, 2, 12, 10, 7]  
create_route("Chuo", stops_chuo, ["23:10", "23:30", "23:50"], times_chuo)  
create_route("Chuo_Last", stops_chuo[:6], ["24:15"], times_chuo[:5]) # 立川止まり  
  
pd.DataFrame(stop_times).to_csv(f"{DATA_DIR}/stop_times.txt", index=False)  
print("✅ stop_times.txt updated.")  
print("完了: 駅データと時刻表IDを日本語で統一しました。")  
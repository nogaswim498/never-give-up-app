import requests  
import pandas as pd  
import json  
import os  
import time  
  
# ==========================================  
# ★ここにODPTのAPIキーを入れてください  
API_KEY = "pvljcnxsfstd3z41mu5uiewsrryz36f5o66yn5axpmosqbt3jgm2ghn0boz5jsn3"  
# ==========================================  
  
DATA_DIR = "data"  
os.makedirs(DATA_DIR, exist_ok=True)  
  
# 取得対象の事業者リスト (JR東日本, 東京メトロ, 都営地下鉄, 東急, 小田急, 京王, 西武...)  
# ※データ量が膨大になるので、まずは主要なところに絞ります  
TARGET_OPERATORS = [  
    "odpt.Operator:JR-East",      # JR東日本  
    "odpt.Operator:TokyoMetro",   # 東京メトロ  
    "odpt.Operator:Toei",         # 都営地下鉄  
    "odpt.Operator:Tokyu",        # 東急電鉄  
    "odpt.Operator:Odakyu",       # 小田急電鉄  
    "odpt.Operator:Keio",         # 京王電鉄  
]  
  
API_URL = "https://api.odpt.org/api/v4/odpt:TrainTimetable"  
STATION_API_URL = "https://api.odpt.org/api/v4/odpt:Station"  
  
def fetch_odpt_data():  
    print("🚀 ODPTから主要各社のデータを取得します...")  
      
    # 1. 駅情報の取得 (ID -> 日本語名マップ作成)  
    station_map = {}  
    print("📡 駅名定義を取得中...")  
      
    for operator in TARGET_OPERATORS:  
        try:  
            res = requests.get(STATION_API_URL, params={  
                "acl:consumerKey": API_KEY,  
                "odpt:operator": operator  
            })  
            if res.status_code == 200:  
                stations = res.json()  
                for st in stations:  
                    station_id = st["owl:sameAs"]  
                    title = st["dc:title"]  
                    # 駅名 ID を記録  
                    station_map[station_id] = title  
                print(f"  - {operator}: {len(stations)} 駅")  
            else:  
                print(f"  - {operator}: 取得失敗 ({res.status_code})")  
        except Exception as e:  
            print(f"  - {operator}: エラー {e}")  
              
    print(f"✅ 合計 {len(station_map)} 駅の定義をメモリに展開しました。")  
  
    # 2. 時刻表の取得  
    print("\n📡 時刻表データを取得中 (これには時間がかかります)...")  
    stop_times_data = []  
      
    for operator in TARGET_OPERATORS:  
        print(f"⏳ {operator} の時刻表をダウンロード中...")  
        try:  
            res = requests.get(API_URL, params={  
                "acl:consumerKey": API_KEY,  
                "odpt:operator": operator,  
                # 平日ダイヤに限定しないとデータ量が爆発するので、まずは平日のみ取得  
                "odpt:calendar": "odpt.Calendar:Weekday"   
            })  
              
            if res.status_code != 200:  
                print(f"  ❌ エラー: {res.status_code}")  
                continue  
                  
            timetables = res.json()  
            count = 0  
              
            for train in timetables:  
                train_id = train["owl:sameAs"]  
                stops = train["odpt:trainTimetableObject"]  
                  
                for i, stop in enumerate(stops):  
                    # 出発駅または到着駅  
                    st_id = stop.get("odpt:departureStation") or stop.get("odpt:arrivalStation")  
                    if not st_id: continue  
                      
                    # 駅IDを日本語名に変換  
                    st_name = station_map.get(st_id)  
                    if not st_name:   
                        # マップになくても、ID末尾が駅名っぽいなら採用する処理  
                        # 例: odpt.Station:JR-East.Chuo.Tokyo -> Tokyo -> 東京  
                        # ここでは安全のためスキップ  
                        continue  
  
                    # 時刻  
                    time_str = stop.get("odpt:departureTime") or stop.get("odpt:arrivalTime")  
                    if not time_str: continue  
                    if len(time_str) == 5: time_str += ":00"  
  
                    stop_times_data.append({  
                        "trip_id": train_id,  
                        "stop_id": st_name,  
                        "arrival_time": time_str,  
                        "departure_time": time_str,  
                        "stop_sequence": i + 1  
                    })  
                count += 1  
              
            print(f"  ✅ {count} 本の列車を取得")  
              
        except Exception as e:  
            print(f"  ❌ 例外発生: {e}")  
            continue  
  
    # 3. 保存  
    if not stop_times_data:  
        print("\n❌ 時刻表データが1件も取得できませんでした。")  
        return  
  
    print(f"\n💾 データをCSVに変換中 ({len(stop_times_data)} 行)...")  
    df = pd.DataFrame(stop_times_data)  
    df = df.sort_values(by=["trip_id", "stop_sequence"])  
      
    output_path = f"{DATA_DIR}/stop_times.txt"  
    df.to_csv(output_path, index=False)  
      
    print(f"🎉 完了！ {output_path} に保存しました。")  
  
if __name__ == "__main__":  
    fetch_odpt_data()  
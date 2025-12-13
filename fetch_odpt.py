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
  
# ターゲット事業者  
TARGET_OPERATORS = [  
    "odpt.Operator:TokyoMetro",  
    "odpt.Operator:Toei",  
    "odpt.Operator:JR-East",  
    "odpt.Operator:Tokyu",  
    "odpt.Operator:Odakyu",  
    "odpt.Operator:Keio",  
    "odpt.Operator:Seibu",  
    "odpt.Operator:Tobu",  
    "odpt.Operator:Sotetsu",  
    "odpt.Operator:Keikyu",  
    "odpt.Operator:Yurikamome",  
    "odpt.Operator:TWR"  
]  
  
# カレンダーリスト (分けて取ることで1000件制限を回避)  
CALENDARS = [  
    "odpt.Calendar:Weekday",  
    "odpt.Calendar:SaturdayHoliday"  
]  
  
API_URL_TIMETABLE = "https://api.odpt.org/api/v4/odpt:TrainTimetable"  
API_URL_STATION = "https://api.odpt.org/api/v4/odpt:Station"  
API_URL_RAILWAY = "https://api.odpt.org/api/v4/odpt:Railway"  
  
def fetch_odpt_data():  
    print("🚀 ODPTからデータを取得します (カレンダー分割モード)...")  
      
    # 1. 駅名マップの作成  
    print("📡 駅定義を取得中...")  
    station_map = {}  
      
    for operator in TARGET_OPERATORS:  
        try:  
            res = requests.get(API_URL_STATION, params={  
                "acl:consumerKey": API_KEY,  
                "odpt:operator": operator  
            })  
            if res.status_code == 200:  
                for st in res.json():  
                    station_map[st["owl:sameAs"]] = st["dc:title"]  
        except:  
            pass  
              
    print(f"✅ {len(station_map)} 駅の定義をロードしました。")  
  
    # 2. 路線リストの取得  
    print("\n📡 路線リストを取得中...")  
    target_railways = []  
      
    for operator in TARGET_OPERATORS:  
        try:  
            res = requests.get(API_URL_RAILWAY, params={  
                "acl:consumerKey": API_KEY,  
                "odpt:operator": operator  
            })  
            if res.status_code == 200:  
                railways = res.json()  
                for r in railways:  
                    target_railways.append(r["owl:sameAs"])  
        except:  
            pass  
  
    print(f"✅ 合計 {len(target_railways)} 路線を対象に時刻表を取得します。")  
  
    # 3. 時刻表の取得 (路線 x カレンダー)  
    stop_times_data = []  
      
    for railway_id in target_railways:  
        line_name = railway_id.split(':')[-1]  
          
        for calendar in CALENDARS:  
            try:  
                res = requests.get(API_URL_TIMETABLE, params={  
                    "acl:consumerKey": API_KEY,  
                    "odpt:railway": railway_id,  
                    "odpt:calendar": calendar # 分割取得  
                })  
                  
                if res.status_code != 200: continue  
                  
                timetables = res.json()  
                if not timetables: continue  
                  
                count = 0  
                for train in timetables:  
                    train_id = train["owl:sameAs"]  
                    stops = train["odpt:trainTimetableObject"]  
                      
                    for i, stop in enumerate(stops):  
                        st_id = stop.get("odpt:departureStation") or stop.get("odpt:arrivalStation")  
                        if not st_id: continue  
                          
                        st_name = station_map.get(st_id)  
                        if not st_name: continue  
  
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
                  
                cal_name = "平日" if "Weekday" in calendar else "土休"  
                print(f"  ✅ {line_name} ({cal_name}): {count} 本")  
                  
                # それでも1000件の上限に達していたら警告  
                if count >= 1000:  
                    print(f"     ⚠️ {line_name} ({cal_name}) は上限1000件に達しました。データ欠落の可能性があります。")  
                  
                time.sleep(0.1)  
                  
            except Exception as e:  
                print(f"  ❌ Error {line_name}: {e}")  
  
    # 4. 保存  
    if not stop_times_data:  
        print("\n❌ データが1件も取れませんでした。")  
        return  
  
    print(f"\n💾 CSV生成中 ({len(stop_times_data)} 行)...")  
    df = pd.DataFrame(stop_times_data)  
      
    # 重複削除（念のため）  
    df = df.drop_duplicates()  
    df = df.sort_values(by=["trip_id", "stop_sequence"])  
      
    output_path = f"{DATA_DIR}/stop_times.txt"  
    df.to_csv(output_path, index=False)  
      
    print(f"🎉 完了！ 合計 {len(stop_times_data)} 行のデータを保存しました。")  
  
if __name__ == "__main__":  
    fetch_odpt_data()  
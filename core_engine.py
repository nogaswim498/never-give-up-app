import pandas as pd  
import requests  
from bs4 import BeautifulSoup  
from datetime import datetime, timedelta  
import math  
import urllib.parse  
import time  
import re  # 正規表現ライブラリを追加  
  
# === 1. 駅位置データの読み込み ===  
print("📂 Loading station data...")  
try:  
    df_stops = pd.read_csv("data/stops.txt")  
    station_coords = {}  
    for _, row in df_stops.iterrows():  
        station_coords[row["stop_name"]] = {  
            "lat": row["stop_lat"],  
            "lon": row["stop_lon"]  
        }  
        if row["stop_name"].endswith("駅"):  
            short = row["stop_name"][:-1]  
            station_coords[short] = station_coords[row["stop_name"]]  
              
    print(f"✅ Loaded {len(station_coords)} stations.")  
except:  
    print("❌ Error: data/stops.txt not found.")  
    station_coords = {}  
  
# === 2. Yahoo!乗換案内 スクレイピング (修正版) ===  
  
def fetch_yahoo_route(start, goal, dt):  
    base_url = "https://transit.yahoo.co.jp/search/print"  
    params = {  
        "from": start,  
        "to": goal,  
        "y": dt.year,  
        "m": str(dt.month).zfill(2),  
        "d": str(dt.day).zfill(2),  
        "hh": str(dt.hour).zfill(2),  
        "m1": str(dt.minute // 10),  
        "m2": str(dt.minute % 10),  
        "type": "1", # 指定時刻 出発  
        "s": "0",    # 到着順  
        "ws": "3",   # 標準  
        "no": "1",   # 1件  
    }  
      
    try:  
        time.sleep(0.5) # アクセス負荷軽減  
        res = requests.get(base_url, params=params, timeout=5)  
        if res.status_code != 200: return None  
          
        soup = BeautifulSoup(res.text, 'html.parser')  
          
        # 経路サマリー取得  
        summary = soup.find("div", class_="routeSummary")  
        if not summary: return None  
  
        # 時間取得  
        time_li = summary.find("li", class_="time")  
        if not time_li: return None  
          
        time_text = time_li.text # 例: "23:58発 → 00:29着(31分)"  
          
        # ★修正: 正規表現で時刻(HH:MM)を2つ抜き出す  
        # \d{1,2}:\d{2} というパターンを探す  
        times = re.findall(r'(\d{1,2}:\d{2})', time_text)  
          
        if len(times) < 2: return None # 出発と到着が取れなかったらエラー  
          
        dep_str = times[0] # 出発時刻  
        arr_str = times[1] # 到着時刻  
          
        # 乗換回数  
        transfer_li = summary.find("li", class_="transfer")  
        transfers = 0  
        if transfer_li:  
            t_text = transfer_li.text  
            # 数字だけ抜き出す  
            nums = re.findall(r'\d+', t_text)  
            if nums: transfers = int(nums[0])  
  
        # 深夜判定  
        dep_h = int(dep_str.split(':')[0])  
        req_h = dt.hour  
          
        # 23時検索 -> 05時出発 はNG (終電終わってる)  
        if req_h >= 20 and 4 <= dep_h < 10: return None  
        # 25時(01時)検索 -> 05時出発 はNG  
        if req_h < 4 and 4 <= dep_h < 10: return None  
  
        return {  
            "found": True,  
            "dep": dep_str,  
            "arr": arr_str,  
            "transfers": transfers  
        }  
  
    except Exception as e:  
        print(f"Scraping Error: {e}")  
        return None  
  
# === 3. 距離・料金 ===  
  
def haversine_distance(c1, c2):  
    R = 6371  
    lat1, lon1 = math.radians(c1["lat"]), math.radians(c1["lon"])  
    lat2, lon2 = math.radians(c2["lat"]), math.radians(c2["lon"])  
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2  
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))  
    return R * c  
  
def calculate_taxi_fare(km):  
    if km < 0.1: return 0  
    fare = 500  
    road_km = km * 1.4  
    if road_km > 1.096:  
        fare += math.ceil(((road_km * 1000) - 1096) / 255) * 100  
    return round(fare * 1.2 * 1.1, -1)  
  
# === 4. 探索ロジック ===  
  
def search_routes(start_name, current_time_str, target_name=None, target_lat=None, target_lon=None):  
    start_coords = station_coords.get(start_name)  
    target_coords = None  
    if target_lat: target_coords = {"lat": target_lat, "lon": target_lon}  
    elif target_name and target_name in station_coords: target_coords = station_coords[target_name]  
      
    if not start_coords or not target_coords:  
        return {"error": "駅の場所が特定できません。"}  
  
    now = datetime.now()  
    try:  
        h, m = map(int, current_time_str.split(':'))  
        target_date = now  
        if h >= 24:  
            h -= 24  
            target_date = now + timedelta(days=1)  
        search_dt = target_date.replace(hour=h, minute=m, second=0)  
    except:  
        search_dt = now  
  
    print(f"🔎 Solving: {start_name} -> {target_name or 'Home'} @ {search_dt}")  
  
    # 候補抽出  
    candidates = []  
    total_dist = haversine_distance(start_coords, target_coords)  
      
    for name, coords in station_coords.items():  
        if name == start_name: continue  
        d_from_start = haversine_distance(start_coords, coords)  
        d_to_goal = haversine_distance(coords, target_coords)  
          
        # 楕円判定 (直進性チェック)  
        if (d_from_start + d_to_goal) < total_dist * 1.3:  
            candidates.append({  
                "name": name,  
                "dist_start": d_from_start,  
                "dist_goal": d_to_goal  
            })  
              
    # 出発地から近い順にソート  
    candidates.sort(key=lambda x: x["dist_start"])  
      
    # 最大15駅に絞る  
    if len(candidates) > 15:  
        step = len(candidates) // 15  
        candidates = candidates[::step]  
          
    print(f"  Target Stations: {[c['name'] for c in candidates]}")  
  
    # 二分探索  
    left = 0  
    right = len(candidates) - 1  
    best_station = None  
      
    while left <= right:  
        mid = (left + right) // 2  
        target_cand = candidates[mid]  
          
        print(f"  Checking: {target_cand['name']} ... ", end="")  
        res = fetch_yahoo_route(start_name, target_cand['name'], search_dt)  
          
        if res:  
            print("OK ✅")  
            best_station = {  
                "station": target_cand['name'],  
                "res": res,  
                "dist": target_cand['dist_goal']  
            }  
            left = mid + 1  
        else:  
            print("NG ❌")  
            right = mid - 1  
  
    results = []  
      
    if best_station:  
        price = calculate_taxi_fare(best_station['dist'])  
        results.append({  
            "station": best_station['station'],  
            "arrival_time": best_station['res']['arr'], # これで純粋な時刻だけになる  
            "distance_to_target_km": round(best_station['dist'], 2),  
            "route_count": best_station['res']['transfers'] + 1,  
            "taxi_price": price,  
            "last_stop_id": "LIMIT"  
        })  
    else:  
        results.append({  
            "station": start_name,  
            "arrival_time": "移動不可",  
            "distance_to_target_km": round(total_dist, 2),  
            "route_count": 0,  
            "taxi_price": calculate_taxi_fare(total_dist),  
            "last_stop_id": "START"  
        })  
  
    return results  
import pandas as pd  
import requests  
from bs4 import BeautifulSoup  
from datetime import datetime, timedelta  
import math  
import urllib.parse  
import time  
import re  
  
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
  
# === 2. Yahoo!乗換案内 スクレイピング (厳格モード) ===  
  
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
        time.sleep(0.5)   
        res = requests.get(base_url, params=params, timeout=5)  
        if res.status_code != 200: return None  
          
        soup = BeautifulSoup(res.text, 'html.parser')  
        summary = soup.find("div", class_="routeSummary")  
        if not summary: return None  
  
        time_li = summary.find("li", class_="time")  
        if not time_li: return None  
          
        time_text = time_li.text   
        times = re.findall(r'(\d{1,2}:\d{2})', time_text)  
        if len(times) < 2: return None   
          
        dep_str = times[0]  
        arr_str = times[1]  
          
        transfer_li = summary.find("li", class_="transfer")  
        transfers = 0  
        if transfer_li:  
            nums = re.findall(r'\d+', transfer_li.text)  
            if nums: transfers = int(nums[0])  
  
        # === ★修正: 厳密な時間チェック ===  
        # 「検索した時間」と「実際の出発時間」の差を見る  
        req_minutes = dt.hour * 60 + dt.minute  
          
        dep_h, dep_m = map(int, dep_str.split(':'))  
        actual_dep_minutes = dep_h * 60 + dep_m  
          
        # 24時またぎの補正  
        # 例: 検索23:50(1430分) -> 出発00:10(10分) の場合、出発は+1440して1450分とみなす  
        if req_minutes > 1200 and actual_dep_minutes < 300: # 20時以降検索で、翌0~5時出発  
            actual_dep_minutes += 1440  
        elif req_minutes < 300 and actual_dep_minutes < req_minutes: # 深夜25時(1時)検索で、出発がそれより前(ありえないが)  
             actual_dep_minutes += 1440  
  
        # 待ち時間 (分)  
        wait_time = actual_dep_minutes - req_minutes  
          
        # 判定1: 待ち時間が120分(2時間)を超えるなら「始発待ち」とみなしてNG  
        if wait_time > 120:   
            # print(f"  [NG] Too long wait: {wait_time}min")  
            return None  
              
        # 判定2: 日付またぎマーク [翌] があり、かつ深夜検索でない場合は警戒  
        if "[翌]" in time_text and req_minutes < 1200:   
             # 昼間に検索して翌日になるのはおかしい  
             return None  
  
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
        # 24時越え対応 (25:00 -> 明日の01:00)  
        if h >= 24:  
            h -= 24  
            target_date = now + timedelta(days=1)  
          
        # 過去時刻補正は行わず、指定時刻で検索  
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
          
        # 直進性チェック  
        if (d_from_start + d_to_goal) < total_dist * 1.3:  
            candidates.append({  
                "name": name,  
                "dist_start": d_from_start,  
                "dist_goal": d_to_goal  
            })  
              
    # 出発地から近い順  
    candidates.sort(key=lambda x: x["dist_start"])  
      
    # API制限対策で間引く  
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
            print("NG (Wait > 2h or No Route) ❌")  
            right = mid - 1  
  
    results = []  
      
    if best_station:  
        price = calculate_taxi_fare(best_station['dist'])  
        results.append({  
            "station": best_station['station'],  
            "arrival_time": best_station['res']['arr'],  
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
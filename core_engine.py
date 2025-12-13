import pandas as pd  
import math  
import requests  
from bs4 import BeautifulSoup  
from datetime import datetime, timedelta  
import urllib.parse  
  
# === 1. 駅データの読み込み (位置関係の把握用) ===  
print("📂 Loading station data...")  
try:  
    df_stops = pd.read_csv("data/stops.txt")  
    # 駅名 -> 座標 の辞書  
    station_coords = {}  
    for _, row in df_stops.iterrows():  
        station_coords[row["stop_name"]] = {  
            "lat": row["stop_lat"],  
            "lon": row["stop_lon"]  
        }  
        # "駅"ありなし対応  
        if row["stop_name"].endswith("駅"):  
            short = row["stop_name"][:-1]  
            station_coords[short] = station_coords[row["stop_name"]]  
              
    print(f"✅ Loaded {len(station_coords)} stations.")  
except:  
    print("❌ Error: data/stops.txt not found.")  
    station_coords = {}  
  
# === 2. Yahoo!乗換案内 スクレイピング機能 ===  
  
def check_yahoo_route(start, goal, year, month, day, hour, minute):  
    """  
    Yahoo!乗換案内で検索し、「指定した日時に出発できるか」を判定する  
    戻り値: (is_reachable, arrival_time_str, price)  
    """  
    # URL構築  
    base_url = "https://transit.yahoo.co.jp/search/print"  
    params = {  
        "from": start,  
        "to": goal,  
        "y": year,  
        "m": str(month).zfill(2),  
        "d": str(day).zfill(2),  
        "hh": str(hour).zfill(2),  
        "m1": str(minute // 10),  
        "m2": str(minute % 10),  
        "type": "1", # 指定時刻 出発  
        "s": "0",    # 到着順  
        "ws": "3",   # 徒歩速度(標準)  
        "no": "1",   # 1件だけ取得  
    }  
      
    try:  
        # スクレイピング実行  
        res = requests.get(base_url, params=params, timeout=5)  
        soup = BeautifulSoup(res.text, 'html.parser')  
          
        # 経路があるか確認  
        route_summary = soup.find("div", class_="routeSummary")  
        if not route_summary:  
            return False, None, None # ルートなし  
  
        # 時間を取得 (例: "23:45発 → 00:30着")  
        time_txt = route_summary.find("li", class_="time").text  
        dep_str = time_txt.split('→')[0].replace('発', '').strip()  
        arr_str = time_txt.split('→')[1].replace('着', '').strip()  
          
        # 日付またぎ判定  
        # 検索した時間(hour)より、出発時間が大幅に早い（＝翌朝）場合はNG  
        # 例: 検索24:30(00:30) -> 結果05:00発 ならアウト  
          
        dep_h = int(dep_str.split(':')[0])  
        req_h = int(hour)  
          
        # 検索が深夜(0~3時)で、結果が始発(4~6時)ならアウト  
        if req_h < 4 and 4 <= dep_h < 10:  
            return False, None, None  
              
        # 検索が夜(23時)で、結果が翌朝(4~6時)ならアウト  
        if req_h > 20 and 4 <= dep_h < 10:  
            return False, None, None  
  
        return True, arr_str, "運賃取得略"  
  
    except Exception as e:  
        print(f"Yahoo Access Error: {e}")  
        return False, None, None  
  
# === 3. 地理計算 & タクシー ===  
  
def haversine_distance(c1, c2):  
    R = 6371  
    lat1, lon1 = math.radians(c1["lat"]), math.radians(c1["lon"])  
    lat2, lon2 = math.radians(c2["lat"]), math.radians(c2["lon"])  
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2  
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))  
  
def calculate_taxi_fare(km):  
    if km < 0.1: return 0  
    fare = 500 # 初乗り  
    if km > 1.096:  
        fare += math.ceil(((km * 1.4 * 1000) - 1096) / 255) * 100  
    return round(fare * 1.2 * 1.1, -1) # 深夜割増 + 迎車等  
  
# === 4. メイン探索ロジック (二分探索) ===  
  
def search_routes(start_name, current_time_str, target_name=None, target_lat=None, target_lon=None):  
    # 座標特定  
    start_coords = station_coords.get(start_name)  
      
    target_coords = None  
    if target_lat: target_coords = {"lat": target_lat, "lon": target_lon}  
    elif target_name and target_name in station_coords: target_coords = station_coords[target_name]  
      
    if not start_coords or not target_coords:  
        return {"error": "駅の場所が特定できません。"}  
  
    # 日時設定  
    now = datetime.now()  
    try:  
        h, m = map(int, current_time_str.split(':'))  
        # 30時間制対応  
        target_date = now  
        if h >= 24:  
            h -= 24  
            target_date = now + timedelta(days=1)  
          
        # 過去の時間なら日付を進める（簡易）  
        if target_date.hour > h:  
            target_date = now + timedelta(days=1)  
              
    except:  
        h, m = now.hour, now.minute  
        target_date = now  
  
    print(f"🔎 Solving: {start_name} -> {target_name or 'Home'} @ {h}:{m}")  
  
    # 1. まず目的地まで行けるかチェック (直行確認)  
    check_name = target_name if target_name else "目的地周辺駅"  
    # 自宅座標の場合、最寄り駅がわからないので、直行チェックはスキップするか、  
    # 近くの駅を探す処理が必要。ここでは簡略化のため「候補探索」へ進む。  
  
    if target_name:  
        ok, arr_t, _ = check_yahoo_route(start_name, target_name, target_date.year, target_date.month, target_date.day, h, m)  
        if ok:  
            # 行けるならそれがベスト  
            return [{  
                "station": target_name,  
                "arrival_time": arr_t,  
                "distance_to_target_km": 0,  
                "route_count": 1,  
                "taxi_price": 0,  
                "last_stop_id": "GOAL"  
            }]  
  
    # 2. 行けない場合、中継地点を探す  
    # 全駅の中から、「出発地と目的地の間にあって」「一直線上にある」駅をピックアップ  
    candidates = []  
      
    total_dist = haversine_distance(start_coords, target_coords)  
      
    for name, coords in station_coords.items():  
        if name == start_name: continue  
          
        d_from_start = haversine_distance(start_coords, coords)  
        d_to_goal = haversine_distance(coords, target_coords)  
          
        # 「回り道」になっていない駅のみ抽出 (楕円判定)  
        # 出発->駅 + 駅->ゴール の距離が、直線の 1.2倍以内なら「経路上」とみなす  
        if (d_from_start + d_to_goal) < total_dist * 1.3:  
            candidates.append({  
                "name": name,  
                "dist_from_start": d_from_start,  
                "dist_to_goal": d_to_goal  
            })  
              
    # 出発地から近い順にソート  
    candidates.sort(key=lambda x: x["dist_from_start"])  
      
    # 候補が多すぎるとYahooに怒られるので、適度に間引く（例: 30駅に絞る）  
    # 特に「ゴールに近い方」を優先したいが、二分探索するには均等な方がいい  
    if len(candidates) > 30:  
        step = len(candidates) // 30  
        candidates = candidates[::step]  
  
    print(f"  Candidates: {len(candidates)} stations extracted.")  
  
    # 3. 二分探索 (Binary Search) で限界駅を見つける  
    # [Start] --(ok)-- [A] --(ok)-- [B] --(ng)-- [C] --(ng)-- [Goal]  
    # Bを見つけたい。  
      
    left = 0  
    right = len(candidates) - 1  
    best_station = None  
      
    # API負荷軽減のため、回数制限  
    checks = 0  
      
    while left <= right and checks < 8: # 最大8回検索  
        mid = (left + right) // 2  
        target_cand = candidates[mid]  
          
        print(f"  Checking: {target_cand['name']} ... ", end="")  
        ok, arr_t, _ = check_yahoo_route(start_name, target_cand['name'], target_date.year, target_date.month, target_date.day, h, m)  
        checks += 1  
          
        if ok:  
            print("OK ✅")  
            # 行けるなら、もっと遠く（右側）を目指す  
            best_station = {  
                "name": target_cand['name'],  
                "arr": arr_t,  
                "dist": target_cand['dist_to_goal']  
            }  
            left = mid + 1  
        else:  
            print("NG ❌")  
            # 行けないなら、もっと手前（左側）を探す  
            right = mid - 1  
  
    results = []  
      
    if best_station:  
        # 見つかった限界駅  
        price = calculate_taxi_fare(best_station['dist'])  
        results.append({  
            "station": best_station['name'],  
            "arrival_time": best_station['arr'],  
            "distance_to_target_km": round(best_station['dist'], 2),  
            "route_count": 99,  
            "taxi_price": price,  
            "last_stop_id": "LIMIT"  
        })  
    else:  
        # 一歩も動けない  
        results.append({  
            "station": start_name,  
            "arrival_time": "移動不可",  
            "distance_to_target_km": round(total_dist, 2),  
            "route_count": 0,  
            "taxi_price": calculate_taxi_fare(total_dist),  
            "last_stop_id": "START"  
        })  
  
    return results  
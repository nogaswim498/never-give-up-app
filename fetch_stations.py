import requests  
import json  
import pandas as pd  
import time  
import os  
import pykakasi # 追加  
  
# 保存先  
DATA_DIR = "data"  
os.makedirs(DATA_DIR, exist_ok=True)  
  
# 変換器の初期化  
kks = pykakasi.kakasi()  
  
# 対象エリア  
PREFECTURES = ["東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県"]  
  
def to_hiragana(text):  
    """ 漢字をひらがなに変換する """  
    result = kks.convert(text)  
    return "".join([item['hira'] for item in result])  
  
def fetch_kanto_stations():  
    print("🚀 関東全域の駅データをダウンロード＆ひらがな変換中...")  
      
    all_stations = []  
    seen_ids = set()   
  
    for pref in PREFECTURES:  
        print(f"📡 {pref} 取得中...")  
          
        # 1. 路線一覧  
        url = "https://express.heartrails.com/api/json"  
        try:  
            res = requests.get(url, params={"method": "getLines", "prefecture": pref}).json()  
            lines = res['response']['line']  
        except:  
            continue  
  
        for line in lines:  
            # 2. 駅一覧  
            try:  
                res_st = requests.get(url, params={"method": "getStations", "line": line}).json()  
                stations = res_st['response']['station']  
            except:  
                continue  
  
            for st in stations:  
                name = st['name']  
                line_name = st['line']  
                  
                # ユニークID (駅名_路線名)  
                # Backendの検索で使うIDと一致させる必要があります  
                # 今回はシンプルに「駅名」をIDとしますが、同名駅（新宿のJRと小田急など）は  
                # 本来区別すべきですが、検索の利便性重視で統合します  
                  
                # フロントエンド用データ作成  
                # ひらがなを自動生成  
                kana = to_hiragana(name)  
                  
                # 重複チェック（同じ駅名が別の路線で出てきても、リストには1つあれば良い場合と、分けたい場合がある）  
                # ここでは「駅名+路線」をユニークキーとして全件保存します  
                unique_key = f"{name}_{line_name}"  
                  
                if unique_key not in seen_ids:  
                    all_stations.append({  
                        "id": name,         # バックエンド検索用ID (漢字)  
                        "n": name,          # 表示名  
                        "k": kana,          # 検索用かな  
                        "l": line_name,     # 路線名  
                        "lat": float(st['y']),  
                        "lon": float(st['x'])  
                    })  
                    seen_ids.add(unique_key)  
              
            time.sleep(0.1) # マナー待機  
  
    print(f"✅ 合計 {len(all_stations)} 駅のデータを生成しました！")  
    return all_stations  
  
if __name__ == "__main__":  
    stations = fetch_kanto_stations()  
      
    # 1. フロントエンド用 (stations_kanto.json)  
    # index.html が読み込む  
    frontend_data = []  
    for s in stations:  
        frontend_data.append({  
            "n": s["n"],  
            "k": s["k"],  
            "l": s["l"]  
        })  
      
    with open(f"{DATA_DIR}/stations_kanto.json", "w", encoding="utf-8") as f:  
        json.dump(frontend_data, f, ensure_ascii=False, separators=(',', ':'))  
    print(f"💾 {DATA_DIR}/stations_kanto.json (入力候補用)")  
  
    # 2. バックエンド用 (stops.txt)  
    # core_engine.py が読み込む  
    # 重複する駅名（路線違い）は、座標を平均するか、代表地点を取るべきですが  
    # 今回は「上書き」で最新のものを採用します（簡易実装）  
    unique_stops = {}  
    for s in stations:  
        unique_stops[s["id"]] = {  
            "stop_id": s["id"],  
            "stop_name": s["n"],  
            "stop_lat": s["lat"],  
            "stop_lon": s["lon"]  
        }  
      
    df = pd.DataFrame(list(unique_stops.values()))  
    df.to_csv(f"{DATA_DIR}/stops.txt", index=False)  
    print(f"💾 {DATA_DIR}/stops.txt (座標計算用)")  
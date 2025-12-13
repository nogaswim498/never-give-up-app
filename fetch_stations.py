import requests  
import json  
import pandas as pd  
import time  
import os  
  
# 保存先  
DATA_DIR = "data"  
os.makedirs(DATA_DIR, exist_ok=True)  
  
# 対象エリア（関東1都6県）  
PREFECTURES = ["東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県"]  
  
def fetch_kanto_stations():  
    print("🚀 関東全域の駅データをダウンロードします...")  
      
    all_stations = []  
    seen_keys = set() # 重複除去用  
  
    for pref in PREFECTURES:  
        print(f"📡 {pref} の路線を取得中...")  
          
        # 1. その県の路線一覧を取得  
        url_lines = "https://express.heartrails.com/api/json"  
        params_lines = {"method": "getLines", "prefecture": pref}  
          
        try:  
            res_lines = requests.get(url_lines, params=params_lines).json()  
            lines = res_lines['response']['line']  
        except Exception as e:  
            print(f"Error fetching lines for {pref}: {e}")  
            continue  
  
        for line in lines:  
            # print(f"  - {line} の駅を取得中...")  
              
            # 2. その路線の駅一覧を取得  
            params_stations = {"method": "getStations", "line": line}  
            try:  
                res_st = requests.get(url_lines, params=params_stations).json()  
                stations = res_st['response']['station']  
            except Exception as e:  
                continue  
  
            for st in stations:  
                # 必要なデータだけ抽出  
                name = st['name']  
                line_name = st['line']  
                lat = float(st['y'])  
                lon = float(st['x'])  
                # 読み仮名 (APIによっては取れない場合もあるが、HeartRailsは 'prev' 'next' 等しかないので、  
                # ここでは簡易的にひらがな変換ライブラリを使うか、今回は「漢字検索」を主とする)  
                # ※HeartRailsには「ふりがな」フィールドがないため、検索用に「ひらがな」は作れません。  
                # 代わりに「そのままの名前」で登録します。  
                  
                # ユニークID作成 (駅名+路線名)  
                unique_id = f"{name}_{line_name}"  
                  
                # 重複チェック（山手線の新宿と中央線の新宿など）  
                # アプリの検索用には「路線名込み」で別々に登録したい  
                  
                # データ整形  
                station_data = {  
                    "name": name,  
                    "line": line_name,  
                    "lat": lat,  
                    "lon": lon,  
                    # IDは英語である必要はないので、ユニークな文字列にする  
                    "id": unique_id  
                }  
                  
                # リストに追加  
                if unique_id not in seen_keys:  
                    all_stations.append(station_data)  
                    seen_keys.add(unique_id)  
              
            # サーバーに優しく（短時間待機）  
            time.sleep(0.1)  
  
    print(f"✅ 合計 {len(all_stations)} 駅のデータを取得しました！")  
    return all_stations  
  
if __name__ == "__main__":  
    stations = fetch_kanto_stations()  
      
    # === 1. フロントエンド用 (JSON) ===  
    # index.html が読み込むためのファイル  
    # 検索しやすいように簡略化  
    frontend_data = []  
    for s in stations:  
        frontend_data.append({  
            "n": s["name"],  
            "l": s["line"],  
            "id": s["id"]  
        })  
      
    with open(f"{DATA_DIR}/stations_kanto.json", "w", encoding="utf-8") as f:  
        json.dump(frontend_data, f, ensure_ascii=False, separators=(',', ':'))  
    print(f"💾 {DATA_DIR}/stations_kanto.json を保存しました (フロントエンド用)")  
  
    # === 2. バックエンド用 (stops.txt) ===  
    # core_engine.py が読み込むためのCSV  
    df = pd.DataFrame([{  
        "stop_id": s["id"],  
        "stop_name": s["name"],  
        "stop_lat": s["lat"],  
        "stop_lon": s["lon"]  
    } for s in stations])  
      
    df.to_csv(f"{DATA_DIR}/stops.txt", index=False)  
    print(f"💾 {DATA_DIR}/stops.txt を保存しました (バックエンド用)")  
      
    print("\n🎉 データ更新完了！")  
    print("注意: stop_times.txt (時刻表) はまだニセモノのままです。")  
    print("駅が増えたので、検索自体はできますが、経路（時刻表）がない駅へのルートは出ません。")  
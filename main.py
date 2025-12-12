from fastapi import FastAPI  
from fastapi.responses import FileResponse  
from fastapi.staticfiles import StaticFiles # 追加  
from pydantic import BaseModel  
from fastapi.middleware.cors import CORSMiddleware  
import core_engine  
import os  
  
app = FastAPI(title="Never!諦めない案内 API")  
  
# スマホアプリ等、外部からのアクセスを許可する設定  
app.add_middleware(  
    CORSMiddleware,  
    allow_origins=["*"],  
    allow_credentials=True,  
    allow_methods=["*"],  
    allow_headers=["*"],  
)  
  
class SearchRequest(BaseModel):  
    start_station: str  
    target_station: str  
    current_time: str  
  
# --- ここを変更: 個別のファイルを配信する設定を追加 ---  
  
# トップページ  
@app.get("/")  
def read_root():  
    return FileResponse("index.html")  
  
# PWA用の設定ファイル  
@app.get("/manifest.json")  
def read_manifest():  
    return FileResponse("manifest.json")  
  
# サービスワーカー  
@app.get("/sw.js")  
def read_sw():  
    return FileResponse("sw.js")  
  
# アイコン画像  
@app.get("/icon.png")  
def read_icon():  
    if os.path.exists("icon.png"):  
        return FileResponse("icon.png")  
    return {"error": "icon.png not found"}  
  
# ついでにログのエラーを消すためのfavicon  
@app.get("/favicon.ico")  
def read_favicon():  
    if os.path.exists("icon.png"):  
        return FileResponse("icon.png") # icon.pngで代用  
    return FileResponse("index.html") # 無ければとりあえずHTML返しとく  
  
# ---------------------------------------------------  
  
@app.post("/search")  
def search_route(req: SearchRequest):  
    # 1. 探索エンジンを実行  
    results = core_engine.search_routes(  
        req.start_station,   
        req.target_station,   
        req.current_time  
    )  
      
    # 2. 結果を判定  
    is_reachable = False  
    best_candidate = None  
      
    if results:  
        top = results[0]  
        if top["distance_to_target_km"] < 1.0:  
            is_reachable = True  
        best_candidate = top  
  
    return {  
        "status": "success",  
        "is_target_reachable": is_reachable,  
        "search_condition": {  
            "start": req.start_station,  
            "target": req.target_station,  
            "time": req.current_time  
        },  
        "candidates": results,  
        "message": "検索完了しました"  
    }  
from fastapi import FastAPI  
from fastapi.responses import FileResponse  
from fastapi.staticfiles import StaticFiles # これを使います  
from pydantic import BaseModel  
from fastapi.middleware.cors import CORSMiddleware  
import core_engine  
import os  
from typing import Optional  
  
app = FastAPI(title="Never!諦めない案内 API")  
  
app.add_middleware(  
    CORSMiddleware,  
    allow_origins=["*"],  
    allow_credentials=True,  
    allow_methods=["*"],  
    allow_headers=["*"],  
)  
  
# === ★ここが修正ポイント: dataフォルダの中身を配信できるようにする ===  
# これがないと stations_kanto.json が読み込めません  
app.mount("/data", StaticFiles(directory="data"), name="data")  
  
class SearchRequest(BaseModel):  
    start_station: str  
    target_station: str  
    current_time: str  
    target_lat: Optional[float] = None  
    target_lon: Optional[float] = None  
  
# --- 個別ファイルの配信設定 ---  
@app.get("/")  
def read_root(): return FileResponse("index.html", media_type="text/html")  
@app.get("/manifest.json")  
def read_manifest(): return FileResponse("manifest.json", media_type="application/manifest+json")  
@app.get("/sw.js")  
def read_sw(): return FileResponse("sw.js", media_type="application/javascript")  
@app.get("/icon.png")  
def read_icon():  
    if os.path.exists("icon.png"): return FileResponse("icon.png", media_type="image/png")  
    return {"error": "not found"}  
@app.get("/favicon.ico")  
def read_favicon():  
    if os.path.exists("icon.png"): return FileResponse("icon.png", media_type="image/png")  
    return FileResponse("index.html")  
  
# --- 検索API ---  
@app.post("/search")  
def search_route(req: SearchRequest):  
    results = core_engine.search_routes(  
        start_name=req.start_station,  
        current_time_str=req.current_time,  
        target_name=req.target_station,  
        target_lat=req.target_lat,  
        target_lon=req.target_lon  
    )  
      
    if isinstance(results, dict) and "error" in results:  
        return {  
            "status": "error",  
            "message": results["error"],  
            "candidates": []  
        }  
      
    is_reachable = False  
    if results:  
        top = results[0]  
        if top["distance_to_target_km"] < 1.0:  
            is_reachable = True  
  
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
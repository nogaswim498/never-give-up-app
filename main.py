from fastapi import FastAPI  
from fastapi.responses import FileResponse  
from fastapi.staticfiles import StaticFiles  
from pydantic import BaseModel  
from fastapi.middleware.cors import CORSMiddleware  
import core_engine  
import os  
  
app = FastAPI(title="Never!諦めない案内 API")  
  
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
  
# --- ここを変更: ファイルの種類(media_type)を明示する ---  
  
@app.get("/")  
def read_root():  
    return FileResponse("index.html", media_type="text/html")  
  
@app.get("/manifest.json")  
def read_manifest():  
    # スマホに「これはアプリ設定ファイルです」と伝える  
    return FileResponse("manifest.json", media_type="application/manifest+json")  
  
@app.get("/sw.js")  
def read_sw():  
    # スマホに「これはプログラムです」と伝える  
    return FileResponse("sw.js", media_type="application/javascript")  
  
@app.get("/icon.png")  
def read_icon():  
    if os.path.exists("icon.png"):  
        return FileResponse("icon.png", media_type="image/png")  
    return {"error": "icon.png not found"}  
  
@app.get("/favicon.ico")  
def read_favicon():  
    if os.path.exists("icon.png"):  
        return FileResponse("icon.png", media_type="image/png")  
    return FileResponse("index.html")  
  
# ---------------------------------------------------  
  
@app.post("/search")  
def search_route(req: SearchRequest):  
    results = core_engine.search_routes(  
        req.start_station,   
        req.target_station,   
        req.current_time  
    )  
      
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
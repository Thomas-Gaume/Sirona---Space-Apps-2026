from fastapi import FastAPI, HTTPException
from threading import Lock
from api import handle_request

app = FastAPI()
lock = Lock()  

@app.post("/query")
def query(req: dict):
    try:
        with lock:
            return handle_request(req)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, f"Requête invalide : {e}")
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from spiceypy.utils.exceptions import SpiceyError
from threading import Lock

from api import handle_request
from query import CRITERIA_INFO, OPS, MAX_EVALS, MAX_DEPTH, MAX_LEAVES
from sites import sites

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
lock = Lock()   # SPICE n'est pas thread-safe : une requête à la fois


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/criteria")
def criteria():
    """Ce que le site peut demander : sert à construire l'interface."""
    return dict(
        criteria=CRITERIA_INFO,
        operators=sorted(OPS),
        modes=["at", "any", "all"],
        combinators=["and", "or", "not"],
        sites=sorted(sites),
        advanced_defaults=dict(step_hours=1.0, range_days=1, grid_step_deg=1.0,
                               terrain=False, earth_min_el=5.0),
        limits=dict(max_evals=MAX_EVALS, max_depth=MAX_DEPTH, max_leaves=MAX_LEAVES),
    )


@app.post("/query")
def query(req: dict):
    try:
        with lock:
            return handle_request(req)
    except (KeyError, ValueError, TypeError, AttributeError, SpiceyError) as e:
        raise HTTPException(400, f"Requête invalide : {type(e).__name__}: {e}")

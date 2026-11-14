from sites import sites
from load_kernels import load_kernels

_kernels_loaded = False

def _ensure_kernels():
    # Charge les kernels une seule fois pour tout le programme
    global _kernels_loaded
    if not _kernels_loaded:
        load_kernels()
        _kernels_loaded = True

def handle_request(req: dict) -> dict:
    _ensure_kernels()

    if "criteria" in req or "points" in req:# recherche par lat/lon
        from query import find_locations
        return find_locations(req)

    from query import check 
    c = req["criterion"]                       # {"type": "illumination", "op": ">", "value": 50}
    date = req["date"]                         # "JJ/MM/AAAA"
    mode = req.get("mode", "any")              # "any" | "all" | "at"
    step = req.get("advanced", {}).get("step_hours", 1.0)
    candidates = req.get("sites") or list(sites)   # par défaut : tous les sites

    unknown = [s for s in candidates if s not in sites]
    if unknown:
        raise ValueError(f"Sites inconnus : {unknown}")

    results = {s: check(s, date, c["type"], c["op"], c["value"], mode, step)
               for s in candidates}

    return dict(date=date, criterion=c, mode=mode,
                results=results,                                   # {"apollo11": True, ...}
                matching_sites=[s for s, ok in results.items() if ok])
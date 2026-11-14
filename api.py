from load_kernels import load_kernels
from query import find_locations, time_series
from sites import sites

_kernels_loaded = False


def _ensure_kernels():
    # Charge les kernels une seule fois pour tout le programme
    global _kernels_loaded
    if not _kernels_loaded:
        load_kernels()
        _kernels_loaded = True


def _normalize(req):
    req = dict(req)
    if "criteria" not in req and "criterion" in req:        # ancien format
        req["criteria"] = [req.pop("criterion")]

    names = req.pop("sites", None)
    if names is not None:
        if not isinstance(names, list) or not names:
            raise ValueError("'sites' doit être une liste non vide de noms")
        unknown = [s for s in names if s not in sites]
        if unknown:
            raise ValueError(f"Sites inconnus : {unknown} (disponibles : {sorted(sites)})")
        req["points"] = list(req.get("points") or []) + [
            dict(name=s, lat=sites[s][0], lon=sites[s][1]) for s in names]
    return req


def handle_request(req: dict) -> dict:
    if not isinstance(req, dict):
        raise ValueError("La requête doit être un objet JSON")
    req = _normalize(req)
    _ensure_kernels()
    if "criteria" in req:
        return find_locations(req)   # mode 2 : critères -> true/false à chaque instant
    return time_series(req)          # mode 1 : points + date -> propriétés à chaque instant

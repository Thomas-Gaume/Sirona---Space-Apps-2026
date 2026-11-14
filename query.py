import numpy as np
import spiceypy as sp
from datetime import datetime
from constants import R_MOON, ABCORR

FAST = {"illumination", "sun_elevation"}
OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
       "<": lambda a, b: a < b,  "<=": lambda a, b: a <= b,
       "==": lambda a, b: a == b}

MAX_EVALS = 500_000_000
CHUNK_EVALS = 2_000_000   # taille max d'un bloc (points x instants) en mémoire


def make_grid(step_deg):
    # centres des cellules, pour ne pas tomber pile sur les pôles
    lats = np.arange(-90 + step_deg / 2, 90, step_deg)
    lons = np.arange(-180 + step_deg / 2, 180, step_deg)
    return [(float(la), float(lo)) for la in lats for lo in lons]


def sun_elevation(points, sun):
    """Élévation du Soleil (°), shape (P, T).
    points : liste de (lat, lon) ; sun : (T, 3) position du Soleil en MOON_ME (km)."""
    lat = np.radians([p[0] for p in points])
    lon = np.radians([p[1] for p in points])
    U = np.stack([np.cos(lat) * np.cos(lon),
                  np.cos(lat) * np.sin(lon),
                  np.sin(lat)], axis=1)                  # (P, 3) verticale locale
    d = U @ sun.T                                        # (P, T) = sun . U
    s2 = np.einsum("tk,tk->t", sun, sun)                 # (T,)  = |sun|^2
    # v = sun - R*U  =>  v.U = d - R  et  |v|^2 = |sun|^2 - 2R d + R^2
    norm = np.sqrt(s2[None, :] - 2 * R_MOON * d + R_MOON ** 2)
    return np.degrees(np.arcsin(np.clip((d - R_MOON) / norm, -1.0, 1.0)))


def _values(el):
    return {"sun_elevation": el,
            "illumination": 100.0 * np.clip(np.sin(np.radians(el)), 0, None)}


def find_locations(req):
    criteria = req["criteria"]
    for c in criteria:
        if c["type"] not in FAST:
            raise ValueError(f"Critère non supporté : {c['type']} "
                             f"(disponibles : {sorted(FAST)})")
        if c["op"] not in OPS:
            raise ValueError(f"Opérateur invalide : {c['op']}")

    mode = req.get("mode", "any")   # "at", "any" ou "all"
    if mode not in ("at", "any", "all"):
        raise ValueError(f"Mode invalide : {mode}")

    adv = req.get("advanced", {})

    step = float(adv.get("step_hours", 1.0))
    days = 0 if mode == "at" else float(adv.get("range_days", 1))
    
    grid_step = float(adv.get("grid_step_deg", 1.0))
    if step <= 0 or grid_step <= 0 or days < 0:
        raise ValueError("step_hours et grid_step_deg doivent être > 0, range_days >= 0")

    user_points = bool(req.get("points"))
    if user_points:
        points = [(p["lat"], p["lon"]) for p in req["points"]]
    else:
        points = make_grid(grid_step)

    start = datetime.strptime(req["date"], "%d/%m/%Y").strftime("%Y-%m-%d 00:00:00")
    et0 = sp.str2et(start)
    n = int(days * 24 / step) + 1
    if len(points) * n > MAX_EVALS:
        raise ValueError(f"Trop de calculs ({len(points) * n}) : augmente "
                         "grid_step_deg ou step_hours, ou réduis range_days")
    ets = et0 + np.arange(n) * step * 3600.0

    sun, _ = sp.spkpos("SUN", ets, "MOON_ME", ABCORR, "MOON")   # (T, 3), un seul appel

    # Nombre d'instants valides par point, calculé par blocs
    hits = np.zeros(len(points), dtype=int)
    chunk = max(1, CHUNK_EVALS // n)
    for i in range(0, len(points), chunk):
        vals = _values(sun_elevation(points[i:i + chunk], sun))
        ok = np.ones(vals["sun_elevation"].shape, dtype=bool)
        for c in criteria:
            ok &= OPS[c["op"]](vals[c["type"]], c["value"])
        hits[i:i + chunk] = ok.sum(axis=1)

    frac = hits / n
    keep = frac > 0 if mode == "any" else frac == 1.0

    base = dict(date=req["date"], mode=mode, criteria=criteria,
                n_times=n, n_tested=len(points), n_matching=int(keep.sum()))

    if user_points:
        return dict(**base,
                    points=[dict(lat=p[0], lon=p[1], fraction=float(f))
                            for p, f, k in zip(points, frac, keep) if k])

    # Grille : tableau à plat, ordre lat (extérieur) puis lon (intérieur)
    n_lat = len(np.arange(-90 + grid_step / 2, 90, grid_step))
    n_lon = len(np.arange(-180 + grid_step / 2, 180, grid_step))
    values = [int(round(f * 100)) if k else None for f, k in zip(frac, keep)]
    return dict(**base,
                grid=dict(step_deg=grid_step,
                          lat0=-90 + grid_step / 2, lon0=-180 + grid_step / 2,
                          n_lat=n_lat, n_lon=n_lon),
                values=values)   # None = critère non respecté, sinon 0-100 (% du temps)
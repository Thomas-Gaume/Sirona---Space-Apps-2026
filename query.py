import functools
import operator
import numpy as np
import spiceypy as sp
from datetime import datetime
from constants import R_MOON, R_SUN, R_EARTH, ABCORR, AU, S0
from eclairement import sun_fraction_horizon
import terrain

CRITERIA_INFO = {
    "sun_elevation":   {"unit": "deg",  "desc": "Élévation géométrique du centre du Soleil"},
    "illumination":    {"unit": "%",    "desc": "% du disque solaire visible (horizon, relief si activé, éclipse par la Terre)"},
    "flux":            {"unit": "W/m2", "desc": "Flux solaire sur une surface horizontale"},
    "earth_elevation": {"unit": "deg",  "desc": "Élévation géométrique de la Terre"},
    "communication":   {"unit": "bool", "desc": "Terre au-dessus de earth_min_el (et du relief si activé) ; utiliser op '==' avec value 1 ou 0"},
}
OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
       "<": lambda a, b: a < b,  "<=": lambda a, b: a <= b,
       "==": lambda a, b: a == b}

MAX_EVALS = 100_000_000     # points x instants max par requête
CHUNK_EVALS = 1_000_000     # taille max d'un bloc en mémoire
MAX_DEPTH = 5               # imbrication max des and/or/not
MAX_LEAVES = 30             # nombre max de critères
MAX_TERRAIN_POINTS = 3000   # points max quand le relief est activé
MAX_USER_POINTS = 1000      # points max quand on renvoie un true/false par instant
SERIES_DAYS = 30            # mode 1 : durée fixe (un mois)


# ---------------------------------------------------------------- critères
def _check(node, depth, leaves):
    """Valide récursivement une expression de critères ; remplit leaves (types utilisés)."""
    if depth > MAX_DEPTH:
        raise ValueError(f"Critères trop imbriqués (max {MAX_DEPTH} niveaux)")
    if not isinstance(node, dict):
        raise ValueError(f"Critère invalide (objet JSON attendu) : {node!r}")
    comb = [k for k in ("and", "or", "not") if k in node]
    if len(comb) > 1:
        raise ValueError(f"Un seul de 'and', 'or', 'not' par niveau : {node}")
    if comb:
        k = comb[0]
        if k == "not":
            children = [node["not"]]
        else:
            children = node[k]
            if not isinstance(children, list) or not children:
                raise ValueError(f"'{k}' doit contenir une liste non vide de critères")
        for ch in children:
            _check(ch, depth + 1, leaves)
        return
    for key in ("type", "op", "value"):
        if key not in node:
            raise ValueError(f"Critère incomplet (manque '{key}') : {node}")
    if node["type"] not in CRITERIA_INFO:
        raise ValueError(f"Critère non supporté : {node['type']} "
                         f"(disponibles : {sorted(CRITERIA_INFO)})")
    if node["op"] not in OPS:
        raise ValueError(f"Opérateur invalide : {node['op']} (disponibles : {sorted(OPS)})")
    float(node["value"])
    leaves.append(node["type"])


def _to_expr(criteria, combine):
    """Une liste devient {combine: liste} ; un dict est déjà une expression."""
    if isinstance(criteria, list):
        if combine not in ("and", "or"):
            raise ValueError(f"'combine' doit valoir 'and' ou 'or' : {combine}")
        if not criteria:
            raise ValueError("'criteria' est vide")
        return {combine: criteria}
    return criteria


def _eval(node, vals):
    """Évalue l'expression : retourne un tableau booléen (P, T)."""
    if "and" in node:
        return functools.reduce(operator.and_, [_eval(n, vals) for n in node["and"]])
    if "or" in node:
        return functools.reduce(operator.or_, [_eval(n, vals) for n in node["or"]])
    if "not" in node:
        return ~_eval(node["not"], vals)
    return OPS[node["op"]](vals[node["type"]], float(node["value"]))


# ---------------------------------------------------------------- géométrie
def make_grid(step_deg):
    # centres des cellules, pour ne pas tomber pile sur les pôles
    lats = np.arange(-90 + step_deg / 2, 90, step_deg)
    lons = np.arange(-180 + step_deg / 2, 180, step_deg)
    return [(float(la), float(lo)) for la in lats for lo in lons]


def _unit(lat_deg, lon_deg):
    lat, lon = np.radians(lat_deg), np.radians(lon_deg)
    return np.stack([np.cos(lat) * np.cos(lon),
                     np.cos(lat) * np.sin(lon),
                     np.sin(lat)], axis=1)               # (P, 3) verticale locale


def _body(U, pos):
    """Pour un astre en position pos (T, 3) (MOON_ME, km) vu depuis les sites R*U :
    retourne (élévation en °, distance en km, U.pos), shapes (P, T)."""
    d = U @ pos.T                                        # (P, T)
    s2 = np.einsum("tk,tk->t", pos, pos)                 # (T,)
    norm = np.sqrt(s2[None, :] - 2 * R_MOON * d + R_MOON ** 2)   # |pos - R*U|
    el = np.degrees(np.arcsin(np.clip((d - R_MOON) / norm, -1.0, 1.0)))
    return el, norm, d


def overlap_area(r1, r2, d):
    """Aire d'intersection de deux disques (rayons r1, r2, distance d), vectorisée."""
    r1, r2, d = np.broadcast_arrays(r1, r2, d)
    out = np.where(d <= np.abs(r1 - r2), np.pi * np.minimum(r1, r2) ** 2, 0.0)
    part = (d > np.abs(r1 - r2)) & (d < r1 + r2)
    if part.any():
        a, b, c = r1[part], r2[part], d[part]
        a1 = a ** 2 * np.arccos(np.clip((c ** 2 + a ** 2 - b ** 2) / (2 * c * a), -1.0, 1.0))
        a2 = b ** 2 * np.arccos(np.clip((c ** 2 + b ** 2 - a ** 2) / (2 * c * b), -1.0, 1.0))
        tri = 0.5 * np.sqrt(np.clip((-c + a + b) * (c + a - b) * (c - a + b) * (c + a + b),
                                    0.0, None))
        out[part] = a1 + a2 - tri
    return out


def compute_values(needed, pts, sun, earth, use_terrain=False, earth_min_el=5.0):
    """Calcule uniquement les grandeurs demandées. Chaque tableau a la forme (P, T).
    needed : ensemble de noms de critères ; earth peut être None si inutile."""
    lat = np.array([p[0] for p in pts], dtype=float)
    lon = np.array([p[1] for p in pts], dtype=float)
    U = _unit(lat, lon)
    el_s, d_s, su = _body(U, sun)
    vals = {}
    if "sun_elevation" in needed:
        vals["sun_elevation"] = el_s

    if needed & {"illumination", "flux"}:
        rho_s = np.arcsin(R_SUN / d_s)
        hor = terrain.horizon_at_sun(lat, lon, sun) if use_terrain else 0.0
        f_hor = sun_fraction_horizon(el_s, rho_s, hor)
        el_e, d_e, eu = _body(U, earth)
        rho_e = np.arcsin(R_EARTH / d_e)
        se = np.einsum("tk,tk->t", sun, earth)
        dot = se[None, :] - R_MOON * (su + eu) + R_MOON ** 2      # v_soleil . v_terre
        sep = np.arccos(np.clip(dot / (d_s * d_e), -1.0, 1.0))
        f_ecl = 1.0 - overlap_area(rho_s, rho_e, sep) / (np.pi * rho_s ** 2)
        f_sun = f_hor * f_ecl
        vals["illumination"] = 100.0 * f_sun
        vals["flux"] = (S0 * (AU / d_s) ** 2 * f_sun
                        * np.maximum(np.sin(np.radians(el_s)), 0.0))

    if needed & {"earth_elevation", "communication"}:
        el_e, _, _ = _body(U, earth)
        vals["earth_elevation"] = el_e
        if "communication" in needed:
            seuil = earth_min_el
            if use_terrain:
                seuil = np.maximum(earth_min_el, terrain.horizon_at_sun(lat, lon, earth))
            vals["communication"] = (el_e > seuil).astype(float)
    return vals


# ---------------------------------------------------------------- préparation commune
def _read_points(raw):
    if not isinstance(raw, list):
        raise ValueError("'points' doit être une liste de {lat, lon}")
    points = [(float(p["lat"]), float(p["lon"])) for p in raw]
    for la, _ in points:
        if not (-90.0 <= la <= 90.0):
            raise ValueError(f"Latitude hors limites : {la}")
    return points


def _setup(req, days, points, needed):
    """Options avancées, relief, dates et éphémérides : commun aux deux modes."""
    adv = req.get("advanced", {})
    step = float(adv.get("step_hours", 1.0))
    earth_min_el = float(adv.get("earth_min_el", 5.0))
    use_terrain = bool(adv.get("terrain", False))
    if step <= 0 or days < 0:
        raise ValueError("step_hours doit être > 0 et range_days >= 0")

    if use_terrain:
        if len(points) > MAX_TERRAIN_POINTS:
            raise ValueError(f"Avec le relief, {MAX_TERRAIN_POINTS} points maximum "
                             f"({len(points)} demandés) : utilise 'points', 'sites' "
                             "ou une grille plus large")
        terrain.ensure_dem()

    n = int(days * 24 / step) + 1
    if len(points) * n > MAX_EVALS:
        raise ValueError(f"Trop de calculs ({len(points) * n}) : augmente "
                         "grid_step_deg ou step_hours, ou réduis range_days")

    start = datetime.strptime(req["date"], "%d/%m/%Y").strftime("%Y-%m-%d 00:00:00")
    ets = sp.str2et(start) + np.arange(n) * step * 3600.0
    sun = np.atleast_2d(sp.spkpos("SUN", ets, "MOON_ME", ABCORR, "MOON")[0])   # (T, 3)
    earth = None
    if needed - {"sun_elevation"}:
        earth = np.atleast_2d(sp.spkpos("EARTH", ets, "MOON_ME", ABCORR, "MOON")[0])
    times = [sp.et2utc(t, "ISOC", 0) for t in ets]
    return dict(n=n, sun=sun, earth=earth, times=times,
                use_terrain=use_terrain, earth_min_el=earth_min_el)


# ---------------------------------------------------------------- mode 1 : propriétés d'un point
def time_series(req):
    """Mode 1 : coordonnées + date -> toutes les propriétés à chaque instant (1 mois)."""
    raw = req.get("points")
    if not raw:
        raise ValueError("Sans 'criteria', la requête doit contenir 'points' ou 'sites'")
    points = _read_points(raw)
    if len(points) > MAX_USER_POINTS:
        raise ValueError(f"{MAX_USER_POINTS} points maximum")

    needed = set(CRITERIA_INFO)
    s = _setup(req, SERIES_DAYS, points, needed)
    vals = compute_values(needed, points, s["sun"], s["earth"],
                          s["use_terrain"], s["earth_min_el"])

    out = []
    for i, (p, q) in enumerate(zip(raw, points)):
        v = {k: np.round(a[i], 3).tolist() for k, a in vals.items()}
        v["communication"] = (vals["communication"][i] > 0.5).tolist()
        d = dict(lat=q[0], lon=q[1], values=v)
        if "name" in p:
            d = {"name": p["name"], **d}
        out.append(d)
    return dict(mode="series", date=req["date"], terrain=s["use_terrain"],
                n_times=s["n"], times=s["times"], points=out)


# ---------------------------------------------------------------- mode 2 : critères
def find_locations(req):
    leaves = []
    expr = _to_expr(req["criteria"], req.get("combine", "and"))
    _check(expr, 0, leaves)
    if len(leaves) > MAX_LEAVES:
        raise ValueError(f"Trop de critères ({len(leaves)}, max {MAX_LEAVES})")
    needed = set(leaves)

    mode = req.get("mode", "any")   # "at", "any" ou "all"
    if mode not in ("at", "any", "all"):
        raise ValueError(f"Mode invalide : {mode}")

    adv = req.get("advanced", {})
    days = 0 if mode == "at" else float(adv.get("range_days", 1))
    grid_step = float(adv.get("grid_step_deg", 0.5))
    if grid_step <= 0:
        raise ValueError("grid_step_deg doit être > 0")

    raw = req.get("points")
    user_points = bool(raw)
    if user_points:
        points = _read_points(raw)
        if len(points) > MAX_USER_POINTS:
            raise ValueError(f"{MAX_USER_POINTS} points maximum")
    else:
        points = make_grid(grid_step)

    s = _setup(req, days, points, needed)
    n = s["n"]

    # Pour chaque point : instants où l'expression est vraie, calculés par blocs
    ok = np.zeros((len(points), n), dtype=bool) if user_points else None
    hits = np.zeros(len(points), dtype=int)
    chunk = max(1, CHUNK_EVALS // n)
    for i in range(0, len(points), chunk):
        vals = compute_values(needed, points[i:i + chunk], s["sun"], s["earth"],
                              s["use_terrain"], s["earth_min_el"])
        res = _eval(expr, vals)
        hits[i:i + chunk] = res.sum(axis=1)
        if user_points:
            ok[i:i + chunk] = res

    frac = hits / n
    keep = frac > 0 if mode == "any" else frac == 1.0

    base = dict(date=req["date"], mode=mode, criteria=req["criteria"],
                combine=req.get("combine", "and"), terrain=s["use_terrain"],
                n_times=n, n_tested=len(points), n_matching=int(keep.sum()))

    if user_points:
        out = []
        for i, (p, q) in enumerate(zip(raw, points)):
            d = dict(lat=q[0], lon=q[1], match=bool(keep[i]), fraction=float(frac[i]),
                     ok=ok[i].tolist())      # true/false à chaque instant de 'times'
            if "name" in p:
                d = {"name": p["name"], **d}
            out.append(d)
        return dict(**base, times=s["times"], points=out)

    # Grille : tableau à plat, ordre lat (extérieur) puis lon (intérieur)
    n_lat = len(np.arange(-90 + grid_step / 2, 90, grid_step))
    n_lon = len(np.arange(-180 + grid_step / 2, 180, grid_step))
    values = [int(round(f * 100)) if k else None for f, k in zip(frac, keep)]
    return dict(**base,
                grid=dict(step_deg=grid_step,
                          lat0=-90 + grid_step / 2, lon0=-180 + grid_step / 2,
                          n_lat=n_lat, n_lon=n_lon),
                values=values)   # None = non retenu, sinon 0-100 (% du temps où l'expression est vraie)

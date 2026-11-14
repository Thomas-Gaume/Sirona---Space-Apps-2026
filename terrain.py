import warnings
import numpy as np
from constants import R_MOON

N_AZ = 36        # directions d'azimut pour le profil d'horizon
MAX_KM = 100.0   # distance max regardée autour de chaque point
N_STEPS = 50     # échantillons le long de chaque direction

_DEM = {}


def _read_dem(path):
    """Lit le raster en tableau 2D : rasterio si disponible, sinon tifffile."""
    try:
        import rasterio
    except ImportError:
        try:
            import tifffile
        except ImportError:
            raise ImportError("Pour lire le relief, installe rasterio ou tifffile "
                              "(pip install tifffile)")
        return np.squeeze(tifffile.imread(path))
    from rasterio.errors import NotGeoreferencedWarning
    warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)
    with rasterio.open(path) as src:
        return src.read(1)


def ensure_dem():
    """Charge le raster en mémoire une seule fois (float16 : ~530 Mo au lieu de ~1 Go)."""
    if "z" in _DEM:
        return
    import constants
    path = getattr(constants, "DEM_FILE", None)
    if not path:
        raise ValueError("Relief non configuré (DEM_FILE dans constants.py)")
    _DEM["z"] = _read_dem(path).astype(np.float16)
    _DEM["ppd"] = getattr(constants, "DEM_PPD", 16)
    _DEM["scale"] = getattr(constants, "DEM_SCALE", 1.0)


def altitude(lat, lon):
    """Altitude (km) aux points (lat, lon) en degrés. Tableaux de n'importe quelle forme.
    Même convention d'indexation que Altitude_read."""
    z, ppd = _DEM["z"], _DEM["ppd"]
    h, w = z.shape
    row = np.clip(np.round((90.0 - np.asarray(lat)) * ppd), 0, h - 1).astype(int)
    col = np.round((np.asarray(lon) % 360.0) * ppd).astype(int) % w
    return z[row, col].astype(np.float32) * _DEM["scale"]


def horizon_profile(lat, lon, n_az=None, max_km=None, n_steps=None):
    """Élévation de l'horizon (rad), >= 0, pour chaque point et azimut. Shape (P, n_az).
    Les réglages par défaut sont lus à l'appel, donc modifiables à l'exécution."""
    n_az = n_az or N_AZ
    max_km = max_km or MAX_KM
    n_steps = n_steps or N_STEPS
    lat = np.asarray(lat, float)
    lon = np.asarray(lon, float)
    lat_r = np.radians(lat)[:, None, None]
    lon_r = np.radians(lon)[:, None, None]
    az = np.radians(np.arange(n_az) * 360.0 / n_az)[None, :, None]    # depuis le nord, vers l'est
    dist = np.linspace(max_km / n_steps, max_km, n_steps)[None, None, :]
    ang = dist / R_MOON

    lat2 = np.arcsin(np.clip(np.sin(lat_r) * np.cos(ang)
                             + np.cos(lat_r) * np.sin(ang) * np.cos(az), -1.0, 1.0))
    lon2 = lon_r + np.arctan2(np.sin(az) * np.sin(ang) * np.cos(lat_r),
                              np.cos(ang) - np.sin(lat_r) * np.sin(lat2))

    r0 = R_MOON + altitude(lat, lon)[:, None, None]
    r1 = R_MOON + altitude(np.degrees(lat2), np.degrees(lon2))
    el = np.arctan2(r1 * np.cos(ang) - r0, r1 * np.sin(ang))
    # Borné à 0 : sans relief on retrouve exactement le calcul sphérique
    return np.maximum(el.max(axis=2), 0.0)


def sun_azimuth(lat, lon, sun):
    """Azimut d'un astre (rad, depuis le nord vers l'est). Shape (P, T). sun : (T, 3) en MOON_ME."""
    la, lo = np.radians(lat), np.radians(lon)
    E = np.stack([-np.sin(lo), np.cos(lo), np.zeros_like(lo)], axis=1)
    N = np.stack([-np.sin(la) * np.cos(lo), -np.sin(la) * np.sin(lo), np.cos(la)], axis=1)
    return np.arctan2(E @ sun.T, N @ sun.T) % (2 * np.pi)


def horizon_at_sun(lat, lon, sun, block=1000):
    """Angle de l'horizon (°) dans la direction d'un astre (Soleil ou Terre). Shape (P, T)."""
    lat = np.asarray(lat, float)
    lon = np.asarray(lon, float)
    out = np.empty((len(lat), len(sun)))
    for j in range(0, len(lat), block):
        s = slice(j, j + block)
        hor = horizon_profile(lat[s], lon[s])                 # (p, n_az)
        az = sun_azimuth(lat[s], lon[s], sun)                 # (p, T)
        idx = np.round(az / (2 * np.pi / hor.shape[1])).astype(int) % hor.shape[1]
        out[s] = np.degrees(np.take_along_axis(hor, idx, axis=1))
    return out
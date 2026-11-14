import numpy as np
import spiceypy as sp

from constants import R_EARTH, ABCORR, R_SUN, AU, S0
from geometry import local_basis, site_vector, az_el
from eclairement import sun_fraction_horizon, disc_overlap_area

def site_info(et, lat, lon, earth_min_el=5.0, horizon_sun_deg=0.0):
    #Infos du site à l'instant et (secondes ET) : comm, éclairement.
    site = site_vector(lat, lon)
    E, N, U = local_basis(lat, lon)
    pos_e, _ = sp.spkpos("EARTH", et, "MOON_ME", ABCORR, "MOON")
    pos_s, _ = sp.spkpos("SUN", et, "MOON_ME", ABCORR, "MOON")
    v_e, v_s = pos_e - site, pos_s - site

    az_e, el_e, d_e = az_el(v_e, E, N, U)
    az_s, el_s, d_s = az_el(v_s, E, N, U)
    rho_s = np.arcsin(R_SUN / d_s)
    rho_e = np.arcsin(R_EARTH / d_e)

    f_hor = sun_fraction_horizon(el_s, rho_s, horizon_sun_deg)
    cosang = v_s @ v_e / (d_s * d_e)
    sep = np.arccos(np.clip(cosang, -1.0, 1.0))
    f_ecl = 1.0 - disc_overlap_area(rho_s, rho_e, sep) / (np.pi * rho_s**2)
    f_sun = float(f_hor * f_ecl)
    flux = S0 * (AU / d_s) ** 2 * f_sun * max(np.sin(np.radians(el_s)), 0.0)

    return dict(utc=sp.et2utc(et, "ISOC", 0),
                el_earth=float(el_e), az_earth=float(az_e), dist_earth_km=float(d_e),
                el_sun=float(el_s), az_sun=float(az_s), dist_sun_km=float(d_s),
                sun_fraction=f_sun, flux_W_m2=float(flux),
                can_communicate=bool(el_e > earth_min_el), sun_up=bool(f_sun > 0.0))

def format_info(r, lat, lon, earth_min_el):
    comm = "OUI" if r["can_communicate"] else "NON"
    sun = "oui" if r["sun_up"] else "non"
    return (f"Site lat {lat:.3f}°, lon {lon:.3f}°  |  {r['utc']} UTC\n"
            f"Comm. directe Terre (seuil {earth_min_el:.0f}°) : {comm}   "
            f"(élév. Terre {r['el_earth']:.2f}°, az {r['az_earth']:.1f}°)\n"
            f"Soleil visible : {sun}   (élév. {r['el_sun']:.2f}°, "
            f"{r['sun_fraction']*100:.1f}% du disque)   "
            f"Flux horizontal : {r['flux_W_m2']:.0f} W/m²")

def site_range(lat, lon, start_utc, days, step_hours=1.0, earth_min_el=5.0):
    et0 = sp.str2et(start_utc)
    n = int(days * 24 / step_hours) + 1
    return [site_info(et0 + i * step_hours * 3600.0, lat, lon, earth_min_el)
            for i in range(n)]
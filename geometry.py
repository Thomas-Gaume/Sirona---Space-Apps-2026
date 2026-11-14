import numpy as np
import spiceypy as sp
from constants import R_MOON

def local_basis(lat_deg, lon_deg):
    #Passer en base Est-Nord-Zénith (2.11 cours OrM)
    lat, lon = np.radians(lat_deg), np.radians(lon_deg)
    E = np.array([-np.sin(lon), np.cos(lon), 0.0])
    N = np.array([-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)])
    U = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    return E, N, U



def site_vector(lat_deg, lon_deg, alt_km=0.0):
    #Permet d'obtenir le vecteur rayon vers le site
    return sp.georec(np.radians(lon_deg), np.radians(lat_deg), 0.0, R_MOON + alt_km, 0.0) #georec ->Géodésique vers cartésien

def az_el(v, E, N, U):
    #Prend un vecteur v (site -> astre) et en déduis az/el/distance
    d = np.linalg.norm(v)
    az = np.degrees(np.arctan2(v @ E, v @ N)) % 360.0
    el = np.degrees(np.arcsin(np.clip(v @ U / d, -1.0, 1.0)))
    return az, el, d
from datetime import datetime
import spiceypy as sp

from load_kernels import load_kernels
from calc import site_range
from sites import sites

#Liste des sites dans "sites.py", c'est à titre d'exemple ça
site_simu = "shackleton"
date_UTC = "22/12/2026" # JJ/MM/AAAA
days = 1   # durée de la plage en jour (0 = un seul instant)
step_hours = 1.0
earth_min_el = 5.0


lat, lon = sites[site_simu]
start_utc = datetime.strptime(date_UTC, "%d/%m/%Y").strftime("%Y-%m-%d 00:00:00")


load_kernels()
try:
    r = site_range(lat, lon, start_utc, days, step_hours, earth_min_el)
finally:
    sp.kclear()

    
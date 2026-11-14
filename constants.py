import os

R_MOON = 1737.4 # km
R_SUN = 695700.0 # km
R_EARTH = 6371.0 # km
AU = 149597870.7 # km
S0 = 1361.0 # W/m²

ABCORR = "LT+S"  

DEM_FILE = os.path.join(os.path.dirname(__file__), "ldem_64.tif")
DEM_PPD = 16     
DEM_SCALE = 1.0 

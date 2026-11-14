import numpy as np
import rasterio
import warnings
from rasterio.windows import Window
from rasterio.errors import NotGeoreferencedWarning

# Altitude_read
# Input
#   long     : array of lunar longitudes [deg]
#   lat      : array of lunar latitudes [deg]
#   PIXEL    : pixel per degree of the map being red [pixel/deg]
#   filename : path to source .tif file
#
# Output
#   altitude : array of altitude at querried points [km]

def Altitude_read(long,lat,PIXEL, filename):

    warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

    with rasterio.open(filename) as src:
        h, w = src.height, src.width
        row = np.minimum(np.round(np.multiply((90 - lat), PIXEL)), h - 1).astype(int)
        col = np.minimum(np.round(np.multiply(180 + long, PIXEL)), w - 1).astype(int)

        altitudes = np.zeros(np.size(row))

        for i in range(np.size(altitudes)) :
            altitudes[i] = src.read(1, window=Window(col[i], row[i], 1, 1))[0, 0]
        
        return altitudes 
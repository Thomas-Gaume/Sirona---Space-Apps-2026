import numpy
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
        row = min(int((90 - lat) * PIXEL), h - 1)
        col = min(int(long * PIXEL), w - 1)

        return src.read(1, window=Window(col, row, 1, 1))[0, 0]
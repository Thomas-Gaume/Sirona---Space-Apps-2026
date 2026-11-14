import numpy as np
import rasterio
import warnings
from rasterio.windows import Window
from rasterio.errors import NotGeoreferencedWarning

# Altitude_read
# Input
#   long     : array of lunar longitudes [deg]
#   lat      : array of lunar latitudes [deg]
#   pixel_num: number of pixels to extract
#   PIXEL    : pixel per degree of the map being red [pixel/deg]
#   filename : path to source .tif file
#
# Output
#   altitude : array of altitude at querried points [km]

def Altitude_read_band(long,lat,pixel_num,PIXEL, filename):

    warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)

    with rasterio.open(filename) as src:

        #read pixel height and width of the map
        h, w = src.height, src.width

        #Compute row and column with a catch to avoid out of bound.
        row = np.minimum(np.round(np.multiply((90 - lat), PIXEL)), h - 1).astype(int)
        col = np.minimum(np.round(np.multiply(180 + long, PIXEL)), w - 1).astype(int)

        start = col - pixel_num + 1          # westernmost pixel of the run

        if start >= 0:
            run = src.read(1, window=Window(start[0], row[0], pixel_num, 1))[0]
        else:                                # run crosses the longitude seam
            k = -start                       # pixels that wrap to the right edge
            part = src.read(1, window=Window(0, row[0], col[0] + 1, 1))[0]
            wrapped = src.read(1, window=Window(w - k, row[0], k, 1))[0]
            run = np.concatenate([wrapped, part])

        return run[::-1]
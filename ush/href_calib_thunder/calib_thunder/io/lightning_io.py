from datetime import datetime
import ncepgrib2
from calib_thunder.data.lightning import Lightning

# Relative filepath of the SREF file to get the grid from
GRID_LOC = 'calib_thunder/io/grid.grib2'


def get_grid(loc=GRID_LOC):
    """Get the NCEP 212 grid from a random SREF GRIB2 file

    :param loc: Full location of the random SREF GRIB2 file
    :return: lat and lon arrays of the grid
    """

    sref = ncepgrib2.Grib2Decode(loc, gribmsg=False)
    lats, lons = sref[0].grid()

    return lats, lons


def load_future(date):
    """Create an empty lightning object for predicting the future

    :param date: datetime object or string in the form 'YYYYMMDD'
    :return: A lightning object with a grid but no data
    """

    if type(date) == str:
        date = datetime.strptime(date, '%Y%m%d')
    lats, lons = get_grid()
    ltg = Lightning(date, lats, lons)

    return ltg


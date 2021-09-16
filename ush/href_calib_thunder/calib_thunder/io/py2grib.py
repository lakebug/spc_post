import ncepgrib2 as ng
import numpy as np

"""
Source: jswhit.github.io/pygrib/ncepgrib2_docs/ncepgrib2.Grib2Encode-class.html
    jswhit.github.io/pygrib/ncepgrib2_docs/ncepgrib2.Grib2Message-class.html
    www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_table4-0.shtml
"""


def py2grib(data, time, fhour, ftime, period, out_dir):
    """Save 2D numpy array as grib2 file (Specifically for HREF calib thunder forecasts)

    :param data: List of 2D arrays containing the gridded forecasts to save
    :param time: Datetime object with the time of the model run
    :param fhour: Model forecast hour
    :param ftime: Datetime object with the valid forecast time
    :param period: Duration of the valid forecast in hours
    :param out_dir: Where to save the grib2 file
    Grib file messages will be in the order provided
    """

    if type(data) is not list:
        data = [data]

    # Define msg codes
    idsect = np.array([7, 9, 2, 1, 1, time.year, time.month, time.day, time.hour,
                       time.minute, time.second, 0, 1])
    gdsinfo = np.array([0, len(data[0].flatten()), 0, 0, 30])
    gdtmpl = np.array([6, 0, 0, 0, 0, 0, 0, 185, 129, 12190000, 226541000, 8, 25000000,
                       265000000, 40635000, 40635000, 0, 64, 25000000, 25000000, 0, 0])
    pdtmpl = np.array([19, 2, 5, 0, 0, 0, 0, 1, fhour, 1, 0, 0, 255, 0, 0, 0, 21, 1, 0,
                       0, 0, 0, ftime.year, ftime.month, ftime.day, ftime.hour,
                       0, 0, 1, 0, 1, 2, 1, period, 255, 0])
    drtmpl = np.array([0, 0, 1, 10, 0, 0, 255])

    # Encode a grib2 object
    encoder = ng.Grib2Encode(0, idsect)
    encoder.addgrid(gdsinfo, gdtmpl)

    for forecast in data:
        encoder.addfield(9, pdtmpl, 40, drtmpl, forecast)
    encoder.end()

    # Save the file
    with open(out_dir, 'wb') as f:
        f.write(encoder.msg)


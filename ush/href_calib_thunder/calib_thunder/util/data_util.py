import pickle
import numpy as np
import traceback
from calib_thunder.util import grid_util


def get_thunder_probs(fix_dir, ensemble, ltg, hour, exper=1, period=4, wd=''):
    """Calculates the ensemble probability of thunder at each grid point

    :param ensemble: List of href objects
    :param ltg: A lightning object to use for grid conversion
    :param hour: The valid forecast hour
    :param exper: The version of the statistical model to use
    :param period: The number of hours to use for the calculation (how long
        the forecast period is)
    :param wd: Working directory - where the hrefct.vX.Y.Z directory is located
    :return: A 2D array with probability of thunder values
    """

    lat1 = ensemble[0].lats
    lon1 = ensemble[0].lons
    lat2 = ltg.lats
    lon2 = ltg.lons
    masks = []

    # Load the grid map
    try:
        with open(fix_dir + '/gridmap.pkl', 'rb') as f:
            gridmap = pickle.load(f)
    except Exception as e:
        traceback.print_exc()
    # Use the specified formula
    # Exper 1 = 4-hour probs
    # Exper 2 = Full-period probs
    # Exper 3 = 1-hour probs
    if exper == 1:
        params = [
            'Reflectivity',
            'Precipitation',
            'Lifted Index'
            ]
        data = {
            'Reflectivity': [],
            'Precipitation': [],
            'Lifted Index': []
            }
        thresh = {
            'Reflectivity': 40,
            'Precipitation': 2,
            'Lifted Index': -1
            }
    elif exper == 3:
        params = [
            'Reflectivity',
            'Precipitation',
            'Lifted Index'
            ]
        data = {
            'Reflectivity': [],
            'Precipitation': [],
            'Lifted Index': []
            }
        thresh = {
            'Reflectivity': 40,
            'Precipitation': 1,
            'Lifted Index': -3
            }
    elif exper == 2:
        params = [
            'Reflectivity',
            'Precipitation'
            ]
        data = {
            'Reflectivity': [],
            'Precipitation': []
            }
        thresh = {
            'Reflectivity': 40,
            'Precipitation': 2
            }

    # Iterate through each href member and process the data
    for href in ensemble:

        # set mask variables
        refl = None
        li = None

        for param in params:

            if href.old and href.model == 'hrrr_ncep':
                this_hour = hour + 6
            elif href.old:
                this_hour = hour + 12
            else:
                this_hour = hour

            # Get the data and convert to 40km grid
            if param == 'Precipitation':
                if period == 4 or exper == 2:
                    i = 1
                    temp = []
                    while i <= period:
                        if i == 1:
                            temp = href.get_hour_data(this_hour + i, param=param)
                        else:
                            temp += href.get_hour_data(this_hour + i, param=param)
                        i += 1
                elif period == 1:
                    temp = (href.get_hour_data(this_hour + (period), param=param))
            elif param == 'Lifted Index':
                temp = href.get_xmin(this_hour, period + 1, param)
            else:
                temp = href.get_xmax(this_hour, period + 1, param)

            broke = False
            if np.isnan(temp).all():
                broke = True
                break

            temp = grid_util.map2grid(lat1, lon1, lat2, lon2, temp,
                                      latlon_map=gridmap)

            # Save variables for mask
            if param == 'Lifted Index':
                li = temp
            elif param == 'Reflectivity':
                refl = temp

            # Compare data to specified thresholds
            if param == 'Lifted Index':
                data[param].append(np.where(temp <= thresh[param], 1, 0))
            else:
                data[param].append(np.where(temp >= thresh[param], 1, 0))

        # Create the mask
        if not broke:
            if exper == 1 or exper == 3:
                if refl is None or li is None:
                    masks.append(np.zeros(lat2.shape))
                else:
                    masks.append(np.where((li >= 0) & (refl < 35), 0, 1))
            elif exper == 2:
                if refl is None:
                    masks.append(np.zeros(lat2.shape))
                else:
                    masks.append(np.where((refl < 35), 0, 1))

    # Apply mask and take the mean of each parameter
    for param in params:
        if len(data[param]) == 0:
            data[param] = np.zeros(lat2.shape)
        else:
            data[param] = np.array(data[param]) * np.array(masks)
            data[param] = np.average(data[param], axis=0)

    # Apply weights and compute the probabilities
    if exper in [1, 3]:
        tprobs = np.average([data[key] for key in params],
                            axis=0, weights=[0.6, 0.3, 0.1])
    else:
        tprobs = np.average([data[key] for key in params],
                            axis=0, weights=[0.6, 0.4])

    return tprobs


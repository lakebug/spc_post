import numpy as np
import pickle as pickle
from scipy.ndimage.filters import gaussian_filter


def apply_calib(fix_dir, tprobs, run, hour, exper=1, smooth=1, wd=''):
    """Apply reliability calibration corrections to a single thunder forecast

    :param tprobs: 2D array containing the original thunder probs
    :param run: Which model run (0 or 12)
    :param hour: Valid hour of the forecast
    :param exper: Which formula to use (1 - 4)
    :param smooth: Sigma to use for Gaussian filter
    :param wd: Working directory - location of the hrefct.vX.Y.Z directory
    :return: 2D array with the updated probabilities
    """

    # Apply smoothing
    calib_probs = gaussian_filter(tprobs, smooth, mode='constant')

    # Apply calibration
    run_str = str(run).zfill(2)
    in_dir = f'{fix_dir}/calib_files/{exper}/{run_str}_{hour}.pkl'

    with open(in_dir, 'rb') as f:
        corr_data = pickle.load(f, encoding='latin1')

    for index in np.ndindex(calib_probs.shape):
        this_forecast = calib_probs * 100
        if this_forecast[index] < 5:
            bin = 0
        elif this_forecast[index] >= 5 and this_forecast[index] < 15:
            bin = 10
        elif this_forecast[index] >= 15 and this_forecast[index] < 25:
            bin = 20
        elif this_forecast[index] >= 25 and this_forecast[index] < 35:
            bin = 30
        elif this_forecast[index] >= 35 and this_forecast[index] < 45:
            bin = 40
        elif this_forecast[index] >= 45 and this_forecast[index] < 55:
            bin = 50
        elif this_forecast[index] >= 55 and this_forecast[index] < 65:
            bin = 60
        elif this_forecast[index] >= 65 and this_forecast[index] < 75:
            bin = 70
        elif this_forecast[index] >= 75 and this_forecast[index] < 85:
            bin = 80
        elif this_forecast[index] >= 85:
            bin = 90

        calib_probs[index] = calib_probs[index] + (corr_data[index][bin] / 100.)
        calib_probs = calib_probs.astype(float)
    
    #  Set anything less than 0 after calibration to 0
    calib_probs[calib_probs < 0] = 0
    
    return calib_probs

import numpy as np
from scipy.spatial import cKDTree


def compute_map(lat1, lon1, lat2, lon2):
    """Compute a mapping from one grid to another

    Takes an array of lats and lons, finds the closest matching point in a
    second array of lats and lons, and returns an array with the indices of
    those points.

    :param lat1: Array of lats to map
    :param lon1: Array of lons to map
    :param lat2: Array of lats to map to
    :param lon2: Array of lons to map to
    :return: Two arrays with the same shape as lat1/lon1 that contains the
                indices of the closest point in lat2/lon2
    """

    # Combine lats and lons for processing
    original = np.dstack([lat1.ravel(), lon1.ravel()])[0].tolist()
    map2 = np.dstack([lat2.ravel(), lon2.ravel()])[0]

    # Build cKDTree
    tree = cKDTree(map2)

    # Get matching indices
    _, indices = tree.query(original)

    # Create map
    index = [i for i in np.ndindex(lat2.shape)]
    indices = np.reshape(indices, lat1.shape)
    latlon_map = np.empty(indices.shape, dtype=tuple)

    for i in np.ndindex(indices.shape):
        latlon_map[i] = index[indices[i]]

    return latlon_map


def map2grid(lat1, lon1, lat2, lon2, data, latlon_map=[], method='max'):
    """Map the values from one grid to another

    :param lat1: Array containing the original latitudes of the data
    :param lon1: Array containing the original longitudes of the data
    :param lat2: Array containing the new latitudes to map to
    :param lon2: Array containing the new latitudes to map to
    :param data: Array with the data to map (must be same shape as lat1 / lon1)
    :param latlon_map: (Optional) Existing map produced by compute_map()
    :param method: How to handle multiple data at the same point
                    Options are 'max' (default) and 'min'
    :return: Array with the same shape as lat2 / lon2 containing the processed data
    """

    # Get map if not provided
    if len(latlon_map) == 0:
        latlon_map = compute_map(lat1, lon1, lat2, lon2)

    # Create an empty array of the new size
    new_data = np.empty(lat2.shape)
    new_data.fill(np.nan)

    # Copy the data over to the new grid
    for i in np.ndindex(data.shape):
        if method == 'max':
            new_data[latlon_map[i]] = max(data[i], new_data[latlon_map[i]])
        elif method == 'min':
            new_data[latlon_map[i]] = min(data[i], new_data[latlon_map[i]])
        else:
            print('FATAL ERROR: Unknown method: ' + method)

    # Fill any remaining NaNs with 0
    new_data = np.nan_to_num(new_data)

    return new_data


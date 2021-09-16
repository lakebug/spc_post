import numpy as np


class HREF:
    """Container class to store up to 1 run of href data in 1 hour forecasts"""

    def __init__(self, model, run, lats, lons, old=False):
        """Constructor for HREF class

        :param run: Datetime date of the model run (including hour)
        :param lats: Array or list of lats in the grid
        :param lons: Array or list of lons in the grid
        :param old: Flag to indicate whether this is a 'current' run or a previous one
        """

        if lats.shape != lons.shape:
            print('ERROR: lats and lons must have the same shape!')

        self.model = model
        self.date = run
        self.lats = lats
        self.lons = lons
        self.data = {}
        self.old = old

    def add_hour_data(self, hour, data):
        """Add one hour of href forecast data to the grid

        :param hour: The forecast hour of the data (e.g. 1, 5, 13, 23, etc)
        :param data: The href data to add.  Should be a dict with structure
                        {var name: data}
        """

        # Add data to self.data dictionary with the forecast hour as the key
        self.data[hour] = data
        return

    def get_hour_data(self, hour, param):
        """Retrieve a single hour of data

        :param hour: The forecast hour to query (e.g. 1, 5, 13, 23, etc)
        :param param: Variable to return. None --> return a dictionary of all variables
        :return: Dictionary/Array containing the gridded href data for the specified hour
        """

        try:
            hour_data = self.data[hour][param]
            return hour_data

        except KeyError:
            return np.full(self.lats.shape, np.nan)

    def get_xmax(self, start, hours, param):
        """Retrieve the maximum param value over a period of x hours

        :param start: Hour to begin querying (inclusive)
        :param hours: Number of forecast hours to query
            Ex. Start time = 12, hours = 4 will query forecast hours 12, 13, 14, 15
        :param param: Variable to query.
        :return: Gridded maximum values over the specified period
        """

        # Process variable
        data = self.get_hour_data(start, param)
        for hour in range(1, hours):
            try:
                data = np.amax([data, self.get_hour_data(start + hour, param)],
                                 axis=0)
            except ValueError as e:
                continue
        return data

    def get_xmin(self, start, hours, param):
        """Retrieve the minimum param value over a period of x hours

        :param start: Hour to begin querying (inclusive)
        :param hours: Number of forecast hours to query
            Ex. Start time = 12, hours = 4 will query forecast hours 12, 13, 14, 15
        :param param: Variable to query.
        :return: Gridded minimum values over the specified period
        """

        # Process variable
        data = self.get_hour_data(start, param)
        for hour in range(1, hours):
            try:
                data = np.amin([data, self.get_hour_data(start + hour, param)],
                                 axis=0)
            except ValueError as e:
                continue
        return data


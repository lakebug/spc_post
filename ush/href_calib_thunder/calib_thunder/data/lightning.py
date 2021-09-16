import numpy as np


class Lightning:
    """Container class to store lightning forecast data"""

    def __init__(self, date, lats, lons):
        """Constructor for lightning class

        :param date: Datetime date of the data
        :param lats: Array or list of lats in the grid
        :param lons: Array or list of lons in the grid
        """

        if lats.shape != lons.shape:
            print('ERROR: lats and lons must have the same shape!')
            lats = []
            lons = []

        self.date = date
        self.lats = lats
        self.lons = lons
        self.data = {}

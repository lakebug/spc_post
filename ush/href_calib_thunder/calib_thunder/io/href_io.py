import numpy as np
import datetime
import os
import ncepgrib2
from calib_thunder.data.href import HREF


def get_fname(model, date, hour):
    """Get the standardized filename for a given forecast hour

    :param model: Name of the model (e.g. conusnssl)
    :param date: Datetime object containing the run date
    :param hour: The forecast hour
    :return: String representing the standard filename
    """
    fhr = str(hour).zfill(2)
    mhr = date.strftime('%H')
    conus_hrw_string = os.environ['COMINhrw_string']  #  Used for either nmmb or fv3 member
    if model == 'conusnest':
        fname = f'nam.t{mhr}z.conusnest.camfld{fhr}.tm00.grib2'
    elif model == 'hrrr_ncep':
        fname = f'hrrr.t{mhr}z.wrfsfcf{fhr}.grib2'
    elif model == 'conusnssl':
        fname = f'hiresw.t{mhr}z.arw_3km.f{fhr}.conusmem2.subset.grib2'
    elif model == 'conusarw':
        fname = f'hiresw.t{mhr}z.arw_3km.f{fhr}.conus.subset.grib2'
    elif model == 'conushrw':
        fname = f'hiresw.t{mhr}z.{conus_hrw_string}_3km.f{fhr}.conus.subset.grib2'

    return fname


def load_hour(directory, filename, model, run, hour, href=None, params=[], old=False,
              verbose=True):
    """Load a single hour of href forecast data

    :param directory: Directory where file is stored
    :param filename: Name of the file to load
    :param model: Name of model to load (e.g. conusnssl, etc)
    :param href: (Optional) Existing href object to add to
    :param params: (Optional) List of variables to load
    :return: HREF class with the added data
    """

    # Parse hour from filename
    #if model == 'hrrr_ncep':
    #    hour = int(str(filename.split('.')[2][-2:]))
    #else:
    #    hour = int(str(filename.split('.')[3][-2:]))

    # Load grib file using ncepgrib2
    run_date = run.strftime('%Y%m%d')
    if model == 'hrrr_ncep':
        data_directory = os.path.join(directory, f'hrrr.{run_date}', 'conus', '')
    elif model == 'conusnest':
        data_directory = os.path.join(directory, f'spc_post.{run_date}', 'spc_nam', '')
    else:
        data_directory = os.path.join(directory, f'hiresw.{run_date}', '')
    # Load grib file
    try:
        gribs = ncepgrib2.Grib2Decode(data_directory + filename, gribmsg=False)
        lats, lons = gribs[1].grid()
    except OSError as e:
        if verbose:
            print(f'WARNING: Unable to load {data_directory}{filename}')
        return href

    # Create a new HREF object if necessary
    if href is None:
        href = HREF(model, run, lats, lons, old)

    # Add the data to the object
    data = {}

    for i, _ in enumerate(gribs):
        if (
            (gribs[i].product_definition_template[0] == 16
             and gribs[i].product_definition_template[1] == 195
             and gribs[i].product_definition_template[2] == 2
             and gribs[i].product_definition_template[11] == 263)
            and len(gribs[i].product_definition_template) != 29
        ):  # Reflectivity at -10C
            data["Reflectivity"] = np.ma.filled(gribs[i].data(), 0)
        elif (
            gribs[i].product_definition_template[0] == 1
            and gribs[i].product_definition_template[1] == 8
            and gribs[i].product_definition_template[2] == 2
            and (gribs[i].product_definition_template[26] == 1
                 or gribs[i].product_definition_template[26] == 0)
        ):  # APCP 1 hr QPF
            data["Precipitation"] = np.ma.filled(gribs[i].data(), 0)
        elif (
            gribs[i].product_definition_template[0] == 7
            and gribs[i].product_definition_template[1] == 193
            and gribs[i].product_definition_template[2] == 2
        ):  # 4LFTX
            data["Lifted Index"] = np.ma.filled(gribs[i].data(), 0)

    href.add_hour_data(hour, data)

    return href


def load_run(directory, model, run, hours=[], params=[], old=False, verbose=True):
    """Load a full model run for a given date and time

    :param directory: Location of the files
    :param model: Name of model to load (e.g. conusnssl, etc)
    :param run: Datetime object (including hour) or formatted string (YYYYMMDDHH)
    :param hours: (Optional) List of forecast hours to load
    :param params: (Optional) List of variables to load
    :param old: Flag to indicate whether the model is a previous run relative
        to the active period
    :param search: If false, will attempt to directly load all files without searching
    :return: HREF class with the added data
    """

    files = []
    if type(run) == str:
        run = datetime.datetime.strptime(run, '%Y%m%d%H')

    # Load files
    files = [get_fname(model, run, hour) for hour in hours]
    # Load the data
    href = None
    if len(files) == 0:
        if verbose:
            print('WARNING: No files found for the specified model and run: '
                  f'{run.strftime("%Y%m%d %H")}z')
        return None

    for filename in files:
        # Parse hour from filename
        if model == 'hrrr_ncep':
            hour = int(str(filename.split('.')[2][-2:]))
        else:
            hour = int(str(filename.split('.')[3][-2:]))
        if (model == 'conusnssl' or model == 'conusarw' or model == 'hrrr_ncep') and hour >=49:
            continue
        if verbose:
            print(f'Loading {filename}')
        href = load_hour(directory, filename, model, run, hour, href, params,
                         old, verbose)

    return href


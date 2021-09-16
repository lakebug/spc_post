from multiprocessing import Pool, Lock
from contextlib import closing
import argparse
import ncepgrib2
from datetime import datetime, timedelta
import numpy as np
import timeit
import time
import sys
import os
from calib_thunder.io import lightning_io
from calib_thunder.io import href_io
from calib_thunder.io import py2grib
from calib_thunder.util import data_util
from calib_thunder.calibration import calibrate


def init(L, b=None):
    """Constructor for multiprocessing"""
    global lock
    lock = L


def get_options():
    """Parse command line arguments"""

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--href_dir', type=str, metavar='', default='',
                        help='Location of HREF files')
    parser.add_argument('-n', '--nam_dir', type=str, metavar='', default='',
                        help='Location of NAM files')
    parser.add_argument('-a', '--hrrr_dir', type=str, metavar='', default='',
                        help='Location of HRRR files')
    parser.add_argument('-p', '--params', type=str, metavar='', default='',
                        help='List of parameters to load')
    parser.add_argument('-g', '--grid_dir', type=str, metavar='', default='',
                        help='Where to output grids')
    parser.add_argument('-d', '--date', type=str, metavar='', default='',
                        help='Date of the HREF run (YYYYMMDDHH)')
    parser.add_argument('-w', '--working_dir', type=str, metavar='', default='',
                        help='Location of the hrefct.vX.Y.Z directory')
    parser.add_argument('-f', '--fix_dir', type=str, metavar='', default='',
                        help='Location of the fix directory')
    parser.add_argument('-c', '--cpu', type=int, metavar='', default='',
                        help='Number of CPUs to use during 1hr/4hr processing')
    parser.add_argument('-m', '--mp', type=str, metavar='', default='',
                        help='Number of CPUs to use during 1hr/4hr processing')
    parser.add_argument('-j', '--job', type=str, metavar='', default='',
                        help='Job Number')
    args = parser.parse_args()

    return args


def load_href(member, date, fhours, href_dir, nam_dir, hrrr_dir, params,
              old=False, verbose=False):
    """Loads a single HREF member for the specified forecast period

    :param member: Name of model to load
    :param date: Datetime object with the date and hour of the model run
    :param fhours: List of forecast times to load
    :param href_dir: Location of HIRESW files
    :param nam_dir: Location of NAM files
    :param hrrr_dir: Location of the HRRR files
    :param params: List of HREF variables to load
    :param old: Flag to indicate whether the model is time-lagged
    :param verbose: Debug printing (recommend false for multiprocessing)
    :return: list of href objects
    """
    verbose=True
    href = []
    if member == 'conusnest':
        href.append(href_io.load_run(nam_dir, 'conusnest', date.strftime('%Y%m%d')
                                     + str(date.hour), hours=fhours,
                                     params=params, old=old, verbose=verbose))
    elif member == 'hrrr_ncep':
        href.append(href_io.load_run(hrrr_dir, 'hrrr_ncep', date.strftime('%Y%m%d')
                                     + str(date.hour), hours=fhours,
                                     params=params, old=old, verbose=verbose))
    else:
        href.append(href_io.load_run(href_dir, member, date.strftime('%Y%m%d')
                                     + str(date.hour), hours=fhours,
                                     params=params, old=old, verbose=verbose))

    return href


def get_members(date, fhour, href_dir, nam_dir, hrrr_dir, params):
    """Load all available members for a given range of forecast hours

    :date: Datetime object with the date and hour of the model run
    :param fhour: List of forecast hours to load
    :param href_dir: Location of the HIRESW members
    :param nam_dir: Location of the NAM CONUS Nest
    :param hrrr_dir: Location of the HRRR
    :param params: List of variables to load
    :return: List of HREF objects
    """

    members = ['conusnssl', 'conusarw', 'conushrw', 'conusnest', 'hrrr_ncep']
    members = [x for pair in zip(members, members) for x in pair]
    href = []

    old_date = date - timedelta(hours=12)
    old_hrrr_date = date - timedelta(hours=6)

    dates = [date, old_date, old_hrrr_date]
    fhours = [fhour, list(np.asarray(fhour) + 12), list(np.asarray(fhour) + 6)]

    """
    Load each member and time-lagged member
    Use index % 2 to determine whether to load time-lagged version
    Iterate through the list of members and load sequentially
    """
    for index in range(len(members)):
        if members[index] == 'hrrr_ncep':
            href.extend(load_href(members[index],
                                  dates[2] if index % 2 else dates[0],
                                  fhours[2] if index % 2 else fhours[0],
                                  href_dir, nam_dir, hrrr_dir,
                                  params, old=index % 2, verbose=True))
        else:
            href.extend(load_href(members[index],
                                  dates[index % 2],
                                  fhours[index % 2],
                                  href_dir, nam_dir, hrrr_dir,
                                  params, old=index % 2, verbose=True))

    # Remove empty href objects
    href = [member for member in href if member is not None]

    return href


def check_exists(fhour, grid_dir, date):
    """Chech if 1hr and 4hr output already exists for faster restart capability

    :param fhour: Forecast hour
    :param grid_dir: Where to grids are located (grib2)
    :date: Datetime object with the date and hour of the model run
    :return: True if already exists, False if it doesn't
    """

    HH = date.strftime("%H")
    fhour = str(fhour).zfill(3)
    if int(fhour) < 4:
        if os.path.isfile(f'{grid_dir}hrefct.t{HH}z.thunder_1hr.f{fhour}.grib2'):
            print(f'hrefct.t{HH}z.thunder_1hr.f{fhour}.grib2 already exists continue.')
            return True
        else:
            return False
    elif int(fhour) >= 4:
        if os.path.isfile(f'{grid_dir}hrefct.t{HH}z.thunder_1hr.f{fhour}.grib2') and os.path.isfile(f'{grid_dir}hrefct.t{HH}z.thunder_4hr.f{fhour}.grib2'):
            print(f'hrefct.t{HH}z.thunder_1hr.f{fhour}.grib2 and hrefct.t{HH}z.thunder_4hr.f{fhour}.grib2 already exists continue.')
            return True
        else:
            return False


def full_check_exists(fhour, grid_dir, date):
    """Chech if full period output already exists for faster restart capability

    :param fhour: Forecast hour
    :param grid_dir: Where to grids are located (grib2)
    :date: Datetime object with the date and hour of the model run
    :return: True if already exists, False if it doesn't
    """

    HH = date.strftime("%H")
    fhour = str(fhour).zfill(3)
    if os.path.isfile(f'{grid_dir}hrefct.t{HH}z.thunder_full.f{fhour}.grib2'):
        print(f'hrefct.t{HH}z.thunder_full.f{fhour}.grib2 already exists continue.')
        return True
    else:
        return False


def gen_hour_forecast(ltg_object, date, fhours, href_dir, nam_dir, hrrr_dir, grid_dir,
                      params, wd, mp=False):
    """Make 1-hour and 4-hour forecasts for each forecast hour

    :param ltg_object: empty lightning object
    :param date: Datetime object with the date and hour of the model run
    :param fhours: List of forecast hours to process
    :param href_dir: Location of the HIRESW members
    :param nam_dir: Location of the NAM CONUS Nest
    :param hrrr_dir: Location of the HRRR
    :param grid_dir: Where to save the grids (grib2)
    :param params: List of variables to load
    :param wd: Working directory - Location of the hrefct.vX.Y.Z directory
    :param mp: Flag to indicate if the function is being called via multiprocessing
    """

    # Dictionary of expected membership numbers based on forecasthour
    switch_date = datetime.strptime('202012030000', '%Y%m%d%H%M')
    if date >= switch_date and os.environ['COMINhrw_string'] == "fv3":
        fmembers = {1: 10, 41: 7, 47: 6}
        exfiles = {1: 20, 4: 50, 37: 48, 38: 46, 39: 44, 40: 42, 41: 40, 43: 39,
                   44: 38, 45: 37, 46: 36, 47: 35}
    elif date >= switch_date and os.environ['COMINhrw_string'] == "nmmb":
        fmembers = {1: 10, 41: 7, 47: 6}
        exfiles = {1: 20, 4: 50, 37: 47, 38: 44, 39: 41, 40: 38, 41: 35, 43: 34,
                   44: 33, 45: 32, 46: 31, 47: 30}
    elif date < switch_date:
        print('before switch date')
        fmembers = {1: 10, 35: 9, 41: 5}
        exfiles = {1: 20, 4: 50, 31: 49, 32: 48, 33: 47, 34: 46, 35: 45, 37: 41,
                   38: 37, 39: 33, 40: 29, 41: 25, 49: 5}
    for fhour in fhours:

        delay = 0         # Timeout counter
        success = False   # Flag to signal if there are enough members to proceed

        already_exists = check_exists(fhour, grid_dir, date)

        #  Check to make reruns start where they left off for faster restart capability
        if already_exists:
            continue

        while not success:
            ensemble = []
            # Try to load the data
            if fhour < 4:
                fhours = list(range(fhour - 1, fhour + 1))
            else:
                fhours = list(range(fhour - 4, fhour + 1))
            ensemble = get_members(date, fhours, href_dir, nam_dir, hrrr_dir, params)
            # Check the number of loaded members
            num_members = len(ensemble)
            i = 0
            total = 0
            while i < num_members:
                total += int(len(ensemble[i].data))
                i += 1
            fkeys = np.array(list(fmembers.keys()))
            exkeys = np.array(list(exfiles.keys()))
            expected = fmembers[fkeys[fkeys <= fhour].max()]
            expected_files = exfiles[exkeys[exkeys <= fhour].max()]
            missing_files = expected_files - total  # MSE
            wait = 120  # how long to wait in minutes before exiting
            sleep = 60  # how many seconds to wait before checking for new file
            if missing_files > 0:
                #  print warning to screen if delay is more than 10 min, which would signify an issue with incoming model data
                if delay >= 10:
                    print(f'WARNING: Missing {missing_files} files for f{str(fhour).zfill(3)}. Wait {sleep} seconds '
                          f'as it may still be coming in. Time Waiting: {delay} min of {wait} min\n')
                if delay >= wait:
                    print(f'FATAL ERROR: Not enough HREF members to proceed for f{str(fhour).zfill(3)}. Waited for {wait} min. Exiting...')
                    sys.exit()
                delay += 1
                time.sleep(sleep)
            else:
                success = True

        # Once the ensemble is loaded, continue with making the grib2 files
        if not mp:
            print(f'\nData ready for forecast hour {str(fhour).zfill(3)}')

        # Identify which hour to use for calibration
        period = date + timedelta(hours=fhour)
        calib_period = period.hour

        # Make forecasts and apply calibration
        # 1-hour forecasts
        if fhour >= 1:
            if not mp:
                print('Generating 1-hour forecast for forecast hour '
                      f'f{str(fhour).zfill(3)}')
            ftime = date + timedelta(hours=fhour)
            probs_1hour = data_util.get_thunder_probs(fix_dir, ensemble, ltg_object,
                                                      fhour-1, exper=3,
                                                      period=1, wd=wd)
            probs_1hour = calibrate.apply_calib(fix_dir, probs_1hour, ensemble[0].date.hour,
                                                calib_period, exper='grid1hr',
                                                smooth=1, wd=wd)
            probs_1hour = np.around(probs_1hour * 100, decimals=0)
            py2grib.py2grib([probs_1hour], date, fhour-1, ftime, 1,
                            f'{grid_dir}hrefct.t{date.strftime("%H")}z.thunder_1hr.'
                            f'f{str(fhour).zfill(3)}.grib2')
            
        # 4-hour forecasts
        if fhour >= 4:
            if not mp:
                print('Generating 4-hour forecast for forcast hour '
                      f'f{str(fhour).zfill(3)}')
            ftime = date + timedelta(hours=fhour)
            probs_4hour = data_util.get_thunder_probs(fix_dir, ensemble, ltg_object,
                                                      fhour-4, exper=1, wd=wd)
            probs_4hour = calibrate.apply_calib(fix_dir, probs_4hour, ensemble[0].date.hour,
                                                calib_period, exper='grid',
                                                smooth=1, wd=wd)
            probs_4hour = np.around(probs_4hour * 100, decimals=0)
            py2grib.py2grib([probs_4hour], date, fhour-4, ftime, 4,
                            f'{grid_dir}hrefct.t{date.strftime("%H")}z.thunder_4hr.'
                            f'f{str(fhour).zfill(3)}.grib2')
        print(f'...{date.strftime("%Y%m%d %H")}z f{str(fhour).zfill(2)} complete!...')


def gen_full_forecast(ltg_object, date, fhours, href_dir, nam_dir, hrrr_dir, grid_dir,
                    params, wd, mp=False):
    """Make full-period forecasts for each forecast hour

    :param ltg_object: empty lightning object
    :param date: Datetime object with the date and hour of the model run
    :param fhours: List of forecast hours to process
    :param href_dir: Location of the HIRESW members
    :param nam_dir: Location of the NAM CONUS Nest
    :param hrrr_dir: Location of the HRRR
    :param grid_dir: Where to save the grids (grib2)
    :param params: List of variables to load
    :param wd: Working directory - Location of the hrefct.vX.Y.Z directory
    :param mp: Flag to indicate if the function is being called via multiprocessing
    """

    # Load the full HREF run
    if not mp:
        print('...Loading HREF ensemble...')
    ensemble = get_members(date, fhours, href_dir, nam_dir, hrrr_dir, params)

    # Load the 4-hour forecasts
    probs_4hour = []
    if not mp:
        print('...Loading 4-hour calibrated thunder forecasts...')
    for fhour in fhours:
        if fhour == fhours[-4]:
            break
        fhr = f'{fhour + 4}'.zfill(3)
        fname = (f'hrefct.t{date.strftime("%H")}z.thunder_4hr.f{fhr}.grib2')
        print(fname)
        try:
            gribs = ncepgrib2.Grib2Decode(os.path.join(grid_dir, fname), gribmsg=False)
        except IOError as e:
            print(f'WARNING: {fname} is not available')
            continue
        else:
            probs_4hour.append(gribs.data())

    # Load the 1-hour forecasts
    probs_1hour = []
    if not mp:
        print('...Loading 1-hour calibrated thunder forecasts...')
    for fhour in fhours[-3:]:
        fhr = f'{fhour}'.zfill(3)
        fname = (f'hrefct.t{date.strftime("%H")}z.thunder_1hr.f{fhr}.grib2')
        print(fname)
        try:
            gribs = ncepgrib2.Grib2Decode(os.path.join(grid_dir, fname), gribmsg=False)
        except IOError as e:
            print(f'WARNING: {fname} is not available')
            continue
        else:
            probs_1hour.append(gribs.data())

    # Check the data
    if len(ensemble) == 0:
        print('FATAL ERROR: Unable to load HREF members for full-period forecast '
              f'{date.strftime("%Y%m%d %H")}z')
        return

    elif len(ensemble) < 5:
        print('FATAL ERROR: Not enough HREF members to generate full-period '
              f'forecast for run {date.strftime("%Y%m%d %H")}z')
        return

    if len(probs_4hour) == 0 or len(probs_1hour) == 0:
        print('WARNING: Unable to load calibrated thunder grib2 files needed for '
              f'full-period forecast {date.strftime("%Y%m%d %H")}z')

    # Generate the full-period forecast for each forecast hour
    last_fcast = None
    num_fhours = range(len(fhours))
    for index in num_fhours:

        if index == num_fhours[-1]:
            break
        fhour = fhours[index]
        
        full_already_exists = full_check_exists(fhour, grid_dir, date)

        #  Check to make reruns start where they left off for faster restart capability
        if full_already_exists:
            # load last forecast and then continue
            HH = date.strftime("%H")
            fcsthour = str(fhour).zfill(3)
            full_period_file = f'{grid_dir}hrefct.t{HH}z.thunder_full.f{fcsthour}.grib2'
            gribs_full = ncepgrib2.Grib2Decode(full_period_file, gribmsg=False)
            last_fcast = gribs_full.data()
            continue  

        # Calculate how many hours between current forecast hour and next 12z
        remainder = (abs(date.hour - 12) + 24) - fhour
        if remainder > 24:
            remainder -= 24
        elif (date.hour == 0 and fhour >= 36 and remainder <= 0):
            remainder += 12
        elif remainder <= 0:
            remainder += 24

        # Identify which hour to use for calibration
        ftime = (date + timedelta(hours=fhour))
        calib_period = ftime.hour

        # Get the full-period forecast
        full_probs = data_util.get_thunder_probs(fix_dir, ensemble, ltg_object, fhour,
                                                 exper=2, period=remainder, wd=wd)
        full_probs = calibrate.apply_calib(fix_dir, full_probs, date.hour, calib_period,
                                           exper='fullperiod', smooth=2, wd=wd)
        full_probs = np.around(full_probs * 100, decimals=0)

        # Get the 4-hour probs max for the period
        if remainder > 4:
            max_hour = np.nanmax(probs_4hour[index:], 0)
        elif remainder == 4:
            max_hour = probs_4hour[index]
        elif remainder < 4:
            if remainder == 3:
                max_hour = np.nanmax(probs_1hour[0:], 0)
            elif remainder == 2:
                max_hour = np.nanmax(probs_1hour[1:], 0)
            elif remainder == 1:
                max_hour = probs_1hour[2]

        # Make sure the full-period probs are not lower than the max 4-hour or
        # 1-hour probs during the last 3 hours
        full_probs = np.nanmax([full_probs, max_hour], 0)

        # Make sure the full-period probs only decrease with time
        # if remainder != 24 and type(last_fcast) != type(None):
        if remainder != 24 and last_fcast is not None:
            full_probs = np.nanmin([full_probs, last_fcast], 0)
        last_fcast = full_probs

        # Figure out the ftime for the grib2 file
        if ftime.hour < 12:
            ftime = ftime.replace(hour=12)
        else:
            ftime = (ftime + timedelta(days=1)).replace(hour=12)

        # Save the grib2 file
        py2grib.py2grib([full_probs], date, fhour, ftime, remainder,
                        f'{grid_dir}hrefct.t{date.strftime("%H")}z.thunder_full.f'
                        f'{str(fhour).zfill(3)}.grib2')

        # Advance to the next forecast hour
        print(f'...{date.strftime("%Y%m%d %H")}z f{str(fhour).zfill(2)} complete!...')


if __name__ == '__main__':
    """Produce calibrated thunder forecasts for the model run and save grids

    :param href_directory: Location of HREF files
    :param nam_directory: Location of NAM files
    :param hrrr_directory: Location of HRRR files
    :param params: List of href variables to load
    :param date: Datetime object with the date and hour of the model run
    :param grid_dir: Where to save the grids (grib2)
    """

    # Load defaults and command line arguments
    args = vars(get_options())
    href_dir = args['href_dir'].strip()
    nam_dir = args['nam_dir'].strip()
    hrrr_dir = args['hrrr_dir'].strip()
    grid_dir = args['grid_dir'].strip()
    params = args['params'].strip()
    working_dir = args['working_dir'].strip()
    fix_dir = args['fix_dir'].strip()
    cpu = args['cpu']
    mp = args['mp'].strip()
    job = int(args['job'])
    if mp == "True":
        mp = True
    else:
        mp = False
    date = datetime.strptime(args['date'].strip(), '%Y%m%d%H')
    start = timeit.default_timer()
    ltg_object = lightning_io.load_future(date)

    # Initiate log
    print('\nHREF Calibrated Thunder v1.0.0 - Grid Generation Script')
    print(f'Processing {date.strftime("%Y%m%d %H")}z HREF cycle')
    print(f'Initiated {datetime.now().strftime("%Y%m%d %H:%M:%S")}')

    # 1/4hr processing
    if job >=1 and job <=48:
        print(f'\nGenerating 1-hr and 4-hr forecasts for job number {job}:')
        fhours = [job]
        gen_hour_forecast(ltg_object, date, fhours, href_dir, nam_dir, hrrr_dir,
                          grid_dir, params, working_dir, False)
        print('1-hr and 4-hr forecasts complete!')

    # Full period processing
    if date.hour == 0:
        if job == 49:
            print('\nGenerating convective day forecasts for f00 - f12:')
            fhours = list(range(0, 13))
            gen_full_forecast(ltg_object, date, fhours, href_dir, nam_dir, hrrr_dir, grid_dir,
                              params, working_dir, False)
            print('Full period forecasts complete!')
        elif job == 50:
            print('\nGenerating convective day forecasts for f12 - f36:')
            fhours = list(range(12, 37))
            gen_full_forecast(ltg_object, date, fhours, href_dir, nam_dir, hrrr_dir, grid_dir,
                              params, working_dir, False)
            print('Full period forecasts complete!')
        elif job == 51:
            print('\nGenerating convective day forecasts for f36 - f48:')
            fhours = list(range(36, 49))
            gen_full_forecast(ltg_object, date, fhours, href_dir, nam_dir, hrrr_dir, grid_dir,
                              params, working_dir, False)
            print('Full period forecasts complete!')
    elif date.hour == 12:
        if job == 49:
            print('\nGenerating convective day forecasts for f00 - f24:')
            fhours = list(range(0, 25))
            gen_full_forecast(ltg_object, date, fhours, href_dir, nam_dir, hrrr_dir, grid_dir,
                              params, working_dir, False)
            print('Full period forecasts complete!')
        if job == 50:
            print('\nGenerating convective day forecasts for f00 - f24:')
            fhours = list(range(24, 49))
            gen_full_forecast(ltg_object, date, fhours, href_dir, nam_dir, hrrr_dir, grid_dir,
                              params, working_dir, False)
            print('Full period forecasts complete!')
    print(f'\nTotal genGrids run time: {str(timeit.default_timer() - start)} seconds')

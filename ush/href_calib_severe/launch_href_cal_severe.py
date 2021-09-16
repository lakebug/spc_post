# Program Name: HREF Calibrated Severe
# Affiliation: NOAA/NWS/Storm Prediction Center
# Contacts: matthew.elliott@noaa.gov (703-887-2332 cell)
# Abstract: Driver script for HREF Calibrated Severe part of SPC POST

import subprocess
from datetime import datetime
import os
import sys


if __name__ == '__main__':
    run_date = os.environ['PDY']
    run = os.environ['cyc']
    forecast_hour = sys.argv[1]
    # update run for 06Z and 18Z
    if run == "06":
       run = "03"
    elif run == "18":
       run = "15" 
    ############################
    if (run == "00" or run == "12") and forecast_hour != "full":
        run_hour = forecast_hour
    elif forecast_hour != "full":
        run_hour = int(forecast_hour) - 3
        run_hour = str(run_hour).zfill(3)
    input_date = f'{run_date}{run}'
    grid_dir = os.path.join(os.environ['COMOUTspc_post'], 'severe', '')
    script_dir = os.path.join(os.environ['USHspc_post'], 'href_calib_severe', '')
    log_dir = os.path.join(os.environ['DATA'], 'logs', '')
    jobid = os.environ['jobid']

    date = datetime.strptime(input_date, '%Y%m%d%H')
    model_run_date = date.strftime("%Y%m%d %H")
    os.makedirs(grid_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    processes = []
    if forecast_hour == "full":
        #logfile = f'calibrated_severe.stderrout.{jobid}_{forecast_hour}'
        logfile = f'calibrated_severe.stderrout'
        print(f'\nPreparing to process {model_run_date}Z HREF Calibrated Severe Full Period Forecast')
    else:
        #logfile = f'calibrated_severe.stderrout.{jobid}_f{run_hour}'
        logfile = f'calibrated_severe.stderrout'
        print(f'\nPreparing to process {model_run_date}Z HREF Calibrated Severe Forecast 4hr forecast for f{run_hour}')
    with open(os.path.join(log_dir, logfile), 'w') as log:
        grid_args = [
            f'-r {run}',
            f'-d {run_date}',
            f'-f {forecast_hour}',
            f'-c',
            ]
        grid_run = subprocess.Popen(['python', '-u', f'{script_dir}forecast_href_cal_severe.py']
                                           + grid_args, stdout=log, stderr=log)

        # Wait for all processes to finish
        #[p.wait() for p in processes]

    streamdata = grid_run.communicate()[0]
    rc = grid_run.returncode
    if rc == 0 :
        if forecast_hour == "full":
            print(f'\nCompleted {model_run_date}Z HREF Calibrated Severe Full Period Forecast!\n')
        else:
            print(f'\nCompleted {model_run_date}Z HREF Calibrated Severe 4hr Forecast for f{run_hour}!\n')
        with open(os.path.join(log_dir, logfile), 'r') as log:
            print(f'\n---Start of {os.path.join(log_dir, logfile)}---')
            print(log.read())
            print(f'\n---End of {os.path.join(log_dir, logfile)}-----\n')
        exit(0)
    else:
        if forecast_hour == "full":
            print(f'\nFATAL ERROR at {model_run_date}Z HREF Calibrated Severe Full Period Forecast!\n')
        else:
            print(f'\nFATAL ERROR at {model_run_date}Z HREF Calibrated Severe 4hr Forecast for f{run_hour}!\n')           
        with open(os.path.join(log_dir, logfile), 'r') as log:
            print(f'\n---Start of {os.path.join(log_dir, logfile)}---')
            print(log.read())
            print(f'\n---End of {os.path.join(log_dir, logfile)}-----\n')
        exit(1)





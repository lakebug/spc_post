# Program Name: HREF Calibrated Thunder
# Affiliation: NOAA/NWS/Storm Prediction Center
# Contacts: matthew.elliott@noaa.gov (703-887-2332 cell)
# Abstract: Driver script for HREF Calibrated Thunder part of SPC POST
# History Log:
#
# Usage:
#   Parameters:
#       run_date --> e.g., $PDY
#       run --> e.g., cyc 
#   Input Files (includes time-lagged member):
#       hiresw.tHHz.arw_3km.fFF.conus.subset.grib2
#       hiresw.tHHz.nmmb_3km.fFF.conus.subset.grib2 or
#           hiresw.tHHz.fv3_3km.fFF.conus.subset.grib2 
#       hiresw.tHHz.arw_3km.fFF.conusmem2.subset.grib2
#       nam.tHHz.conusnest.camfldFF.tm00.grib2
#       hrrr.tHHz.wrfsfcfFF.grib2
#   Output Files:
#       hrefct.tHHz.thunder_1hr.fFFF.grib2  
#       hrefct.tHHz.thunder_4hr.fFFF.grib2  
#       hrefct.tHHz.thunder_full.fFFF.grib2 
#


import subprocess
from datetime import datetime
import os
import sys


run_date = os.environ['PDY']
run = os.environ['cyc']
job = sys.argv[1]
input_date = f'{run_date}{run}'
href_directory = os.environ['COMINhiresw']
hrrr_directory = os.environ['COMINhrrr']
# Use SPC post-processed nam for 1hr precip
nam_directory = os.path.join(os.path.dirname(os.environ['COMOUT']), '') 
grid_dir = os.path.join(os.environ['COMOUTspc_post'], 'thunder', '')
wd = os.path.join(os.environ['USHspc_post'], 'href_calib_thunder', '')
fix_dir = os.path.join(os.environ['FIXspc_post'], 'href_calib_thunder', '')
log_dir = os.path.join(os.environ['DATA'], 'logs', '') # temporarily put in COMOUT, need to move to  DATA
jobid = os.environ['jobid']
params = [
    'Reflectivity',
    'Precipitation',
    'Lifted Index'
    ]
mp = False
cpu = 6

os.chdir(wd)

date = datetime.strptime(input_date, '%Y%m%d%H')
model_run_date = date.strftime("%Y%m%d %H")
os.makedirs(grid_dir, exist_ok=True)
os.makedirs(log_dir, exist_ok=True)    # temporarily put in COMOUT, need to move to  DATA

#processes = []

print(f'\nPreparing to process {model_run_date}Z HREF '
      'Calibrated Thunderstorm Forecast')

'''
Start the HREF Calibrated Thunderstorm forecast script
The forecast script monitors for new HREF ensemble files and generates
1-hour, 4-hour, and full-period calibrated thunder grib2 files as the
forecast hours become available
'''

print('\nLaunching grid generation script.')
print(f'\nScript output being logged to {log_dir}calibrated_thunder.stderrout')


with open(os.path.join(log_dir, f'calibrated_thunder.stderrout'), 'w') as log:
    grid_args = [
        f'-i {href_directory}',
        f'-n {nam_directory}',
        f'-a {hrrr_directory}',
        f'-p {params}',
        f'-g {grid_dir}',
        f'-d {input_date}',
        f'-w {wd}',
        f'-f {fix_dir}',
        f'-c {cpu}',
        f'-m {mp}',
        f'-j {job}',
        ]
    grid_run = subprocess.Popen(['python', '-u', 'gen_thunder_grids.py']
                                       + grid_args, stdout=log, stderr=log)

    # Wait for all processes to finish
    #[p.wait() for p in processes]
streamdata = grid_run.communicate()[0]
rc = grid_run.returncode
if rc == 0: 
    print(f'\nCompleted Job {job} {model_run_date}Z HREF '
      'Calibrated Thunderstorm Forecast!\n')
    with open(os.path.join(log_dir, f'calibrated_thunder.stderrout'), 'r') as log:
        print(f'\n---Start of {log_dir}calibrated_thunder.stderrout---')
        print(log.read())
        print(f'\n---End of {log_dir}calibrated_thunder.stderrout-----')
    exit(0)
else:
    print(f'\nFATAL ERROR at  Job {job} {model_run_date}Z HREF '
      'Calibrated Thunderstorm Forecast!\n')
    with open(os.path.join(log_dir, f'calibrated_thunder.stderrout'), 'r') as log:
        print(f'\n---Start of {log_dir}calibrated_thunder.stderrout---')
        print(log.read())
        print(f'\n---End of {log_dir}calibrated_thunder.stderrout-----')
    exit(1)

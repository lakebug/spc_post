# Program Name: HREF/SREF Calibrated Severe
# Affiliation: NOAA/NWS/Storm Prediction Center
# Contacts: matthew.elliott@noaa.gov (703-887-2332 cell)
# Abstract: Driver script for HREF Calibrated Severe part of SPC POST
#
# Usage:
#   Input Files (includes time-lagged member):
#       hiresw.tHHz.arw_3km.fFF.conus.subset.grib2
#       hiresw.tHHz.nmmb_3km.fFF.conus.subset.grib2 or
#           hiresw.tHHz.fv3_3km.fFF.conus.subset.grib2 
#       hiresw.tHHz.arw_3km.fFF.conusmem2.subset.grib2
#       nam.tHHz.conusnest.camfldFF.tm00.grib2
#       hrrr.tHHz.wrfsfcfFF.grib2
#       spcsref(all members)
#   Output Files:
#       href_cal_wind.tHHz.4hr.fFFF.grib2
#       href_cal_hail.tHHz.4hr.fFFF.grib2
#       href_cal_tornado.tHHz.4hr.fFFF.grib2

import os, sys, glob
import datetime
import argparse
import ncepgrib2 as ng
import numpy as np
from astropy.convolution import convolve, Gaussian2DKernel
from scipy.interpolate import NearestNDInterpolator
from scipy.ndimage.morphology import binary_dilation
from subprocess import Popen, PIPE
import pickle
import time

start = datetime.datetime.utcnow()

# define command line arguments/inputs
parser = argparse.ArgumentParser()
parser.add_argument("-r", "--run", required=True, default=None, help='e.g., 03, 09, 15, 21')
parser.add_argument("-d", "--date", required=True, default=None, help='e.g., 20190520')
parser.add_argument("-f", "--fhour", required=True, default=None, help='e.g., 4, 5, 6')
parser.add_argument("-c", "--cap", required=False, default=False, action='store_true', help='limit magnitudes of calibrated probabilities (60% for tor/hail, 75% for wind)')
args = parser.parse_args()
args.run = args.run.strip()
args.date = args.date.strip()
args.fhour = args.fhour.strip()

if args.fhour != "full":
    if args.run == 00 or args.run == 12:
        print(f'Running HREF/SREF Calibrated Severe 4hr Probabilities for {args.date} {args.run}Z f{args.fhour}')
    else:
        run_hour = int(args.fhour) - 3
        run_hour = str(run_hour).zfill(3)
        print(f'Running HREF/SREF Calibrated Severe 4hr Probabilities for {args.date} {args.run}Z f{run_hour}')
else:
        print(f'Running HREF/SREF Calibrated Severe Full Period Probabilities for {args.date} {args.run}Z')

# construct time objects
now = datetime.datetime(int(args.date[:4]),int(args.date[4:6]),int(args.date[6:8]),int(args.run))

# define base paths
tmpDir = os.environ['DATA'] + f'/href_calib_severe/f{args.fhour}/'
os.makedirs(tmpDir, exist_ok=True)
grbDir = os.path.join(os.environ['COMOUT'], 'severe', '') 
os.makedirs(grbDir, exist_ok=True)
nam_dir = os.environ['COMINnam']
sref_dir = os.environ['COMINspcsref']
hrrr_dir = os.environ['COMINhrrr']
hiresw_dir = os.environ['COMINhiresw']
fix_dir = os.environ['FIXspc_post'] + '/href_calib_severe/'
scripts_dir = os.environ['USHspc_post'] + '/href_calib_severe/'
spc_pickle_dir = os.environ['COMOUTspc_pickle']  
os.makedirs(spc_pickle_dir, exist_ok=True)
if os.environ['COMINhrw_string'] == "fv3":
    fv3 = True
elif os.environ['COMINhrw_string'] == "nmmb":
    fv3 = False

if args.fhour != "full":
    # define pickle file
    if args.run in ['00','12']:
        uhProbsFile = spc_pickle_dir + '/uhProbs_' + args.date + args.run + 'f' + args.fhour + '.pickle'  

    else:
        uhTime = now - datetime.timedelta(hours=3)
        uhProbsFile = spc_pickle_dir + '/uhProbs_' + uhTime.strftime('%Y%m%d%H') + 'f' + args.fhour + '.pickle' 
else:
    uhProbsDict = {}
    if args.run == '00' or args.run == '03':
        run_start = 16
        run_end = 36
        run_time = "00"
    elif args.run == '12':
        run_start = 4
        run_end = 24
        run_time = "12"
    elif args.run == '15':
        run_start = 8
        run_end = 24
        run_time = "12"
    uhProbsFile = False
    uhProbsFile_full = spc_pickle_dir + '/uhProbs_' + args.date + args.run + '.pickle'
    if not os.path.exists(uhProbsFile_full):
        for fcst_hour in range(run_start, (run_end+1)):
            fcst_hour = str(fcst_hour).zfill(3)
            uhProbsFile = spc_pickle_dir + '/uhProbs_' + args.date + run_time + 'f' + str(fcst_hour) + '.pickle'
            with open(uhProbsFile, 'rb') as f:
                uhProbsDict.update(pickle.load(f))
        with open(uhProbsFile_full, 'wb') as fh:
            pickle.dump(uhProbsDict, fh, protocol=pickle.HIGHEST_PROTOCOL)

# read grids and grid map
grbs = ng.Grib2Decode(fix_dir + '/srefGrid.grib2')

srefLats, srefLons = grbs.latlons()
srefX = srefLons.flatten()
srefY = srefLats.flatten()

# define SREF/HREF dictionary based on SREF run
if args.fhour == "full": 
    run = {
        '03':{
            'rStart': 13,
            'rHours': 23,
            'fStart': 16,
            'hrefStart': 13,
            'hrefEnd': 36,
            'hrefRun': 0,
            'hrefStartTL': 25,
            'hrefEndTL': 48,
            'hrefRunTL': 12,
            'srefStart': 13,
            'srefEnd': 33
        },
        '12':{
            'rStart': 13,
            'rHours': 23,
            'fStart': 16,
            'hrefStart': 1,
            'hrefEnd': 24, 
            'hrefRun': 12,
            'hrefStartTL': 13,
            'hrefEndTL': 36,
            'hrefRunTL': 0,
            'srefStart': 7,
            'srefEnd': 27 
        },
        '15':{
            'rStart': 17,
            'rHours': 19,
            'fStart': 20,
            'hrefStart': 5,
            'hrefEnd': 24, 
            'hrefRun': 12,
            'hrefStartTL': 17,
            'hrefEndTL': 36,
            'hrefRunTL': 0,
            'srefStart': 5,
            'srefEnd': 21 
        },
        '00':{
            'rStart': 13,
            'rHours': 23,
            'fStart': 16,
            'hrefStart': 13,
            'hrefEnd': 36,
            'hrefRun': 0,
            'hrefStartTL': 25,
            'hrefEndTL': 48,
            'hrefRunTL': 12,
            'srefStart': 19,
            'srefEnd': 39
        }
    }
else:
    run = {
        '03':{
            'rStart': int(args.fhour) - 3,
            'rHours': int(args.fhour) - 3,
            'fStart': int(args.fhour),
            'hrefStart': int(args.fhour) - 3,
            'hrefEnd': int(args.fhour),
            'hrefRun': 0,
            'hrefStartTL': int(args.fhour) + 9,
            'hrefEndTL': int(args.fhour) + 12,
            'hrefRunTL': 12,
            'srefStart': int(args.fhour) - 3,
            'srefEnd': int(args.fhour) - 3
        },
        '12':{
            'rStart': int(args.fhour) + 9,
            'rHours': int(args.fhour) + 9,
            'fStart': int(args.fhour) + 12,
            'hrefStart': int(args.fhour) - 3,
            'hrefEnd': int(args.fhour), 
            'hrefRun': 12,
            'hrefStartTL': int(args.fhour) + 9,
            'hrefEndTL': int(args.fhour) + 12,
            'hrefRunTL': 0,
            'srefStart': int(args.fhour) + 3,
            'srefEnd': int(args.fhour) + 3 
        },
        '15':{
            'rStart': int(args.fhour) + 9,
            'rHours': int(args.fhour) + 9,
            'fStart': int(args.fhour) + 12,
            'hrefStart': int(args.fhour) - 3,
            'hrefEnd': int(args.fhour), 
            'hrefRun': 12,
            'hrefStartTL': int(args.fhour) + 9,
            'hrefEndTL': int(args.fhour) + 12,
            'hrefRunTL': 0,
            'srefStart': int(args.fhour) - 3,
            'srefEnd': int(args.fhour) - 3 
        },
        '00':{
            'rStart': int(args.fhour) - 3,
            'rHours': int(args.fhour) - 3,
            'fStart': int(args.fhour),
            'hrefStart': int(args.fhour) - 3,
            'hrefEnd': int(args.fhour),
            'hrefRun': 0,
            'hrefStartTL': int(args.fhour) + 9,
            'hrefEndTL': int(args.fhour) + 12,
            'hrefRunTL': 12,
            'srefStart': int(args.fhour) + 3,
            'srefEnd': int(args.fhour) + 3
        },
    }
    
# contstruct additional time objects
if run[args.run]['fStart'] > 23:
    tomorrow = now + datetime.timedelta(days=1)
    run[args.run]['fStart'] = run[args.run]['fStart'] - 24
    run[args.run]['rHours'] = run[args.run]['rHours'] - 24
    rTimeOrig = datetime.datetime(tomorrow.year,tomorrow.month,tomorrow.day,run[args.run]['fStart'],0,0)
    rTime2 = datetime.datetime(tomorrow.year,tomorrow.month,tomorrow.day,run[args.run]['fStart'],0,0)
else:
    rTimeOrig = datetime.datetime(now.year,now.month,now.day,run[args.run]['fStart'],0,0)
    rTime2 = datetime.datetime(now.year,now.month,now.day,run[args.run]['fStart'],0,0)
rEnd = rTime2 + datetime.timedelta(hours=run[args.run]['rHours'])
init = datetime.datetime(now.year,now.month,now.day,run[args.run]['hrefRun'],0,0)
hrefRun = init.strftime('%Y%m%d%H')

# define paths for current time
hrefDir = hiresw_dir + '/hiresw.' + init.strftime('%Y%m%d')

hrrrDir = hrrr_dir + '/hrrr.' + init.strftime('%Y%m%d') + '/conus'
namNestDir = nam_dir + '/nam.' + init.strftime('%Y%m%d')

# define HRRR time-lag variables
initHrrrTL = init - datetime.timedelta(hours=6)
hrrrRunTL = initHrrrTL.strftime('%Y%m%d%H')
hrrrDirTL = hrrr_dir + '/hrrr.' + initHrrrTL.strftime('%Y%m%d') + '/conus'

# define HREF time-lage variables
initHrefTL = init - datetime.timedelta(hours=12)
hrefRunTL = initHrefTL.strftime('%Y%m%d%H')
fTime = datetime.datetime(now.year,now.month,now.day,run[args.run]['fStart'],0,0)
hrefDirTL = hiresw_dir + '/hiresw.' + initHrefTL.strftime('%Y%m%d')
namNestDirTL = nam_dir + '/nam.' + initHrefTL.strftime('%Y%m%d')

# define SREF time variables
if args.run == '00':
    srefDay = now - datetime.timedelta(days=1)
    srefRun = srefDay.strftime('%Y%m%d') + "21"
elif args.run == '12':
    srefDay = now
    srefRun = now.strftime('%Y%m%d') + "09"
elif args.run == "15" or args.run == "03":
    srefDay = now
    srefRun = now.strftime('%Y%m%d') + args.run

srefDir = sref_dir + '/spcsref.' + srefDay.strftime('%Y%m%d') + '/gempak'

print(init, hrefRunTL)

# define href member attributes
hrefMembers = {
    '1':{
        'path': hrefDir,
        'name': ['arw','conusmem2.subset'],
        'run': hrefRun,
        'fHours': np.arange(run[args.run]['hrefStart'],run[args.run]['hrefEnd']+1),
        'uhThresh': 75,
        'pdt':'[7, 199, 2, 0, 116, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.2
    },
    '2':{
        'path': hrefDirTL,
        'name': ['arw','conusmem2.subset'],
        'run': hrefRunTL,
        'fHours': np.arange(run[args.run]['hrefStartTL'],run[args.run]['hrefEndTL']+1),
        'uhThresh': 75,
        'pdt':'[7, 199, 2, 0, 116, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.2
    },
    '3':{
        'path': hrefDir,
        'name':['arw','conus.subset'],
        'run': hrefRun,
        'fHours': np.arange(run[args.run]['hrefStart'],run[args.run]['hrefEnd']+1),
        'uhThresh': 75,
        'pdt':'[7, 199, 2, 0, 116, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.2
    },
    '4':{
        'path': hrefDirTL,
        'name':['arw','conus.subset'],
        'run': hrefRunTL,
        'fHours': np.arange(run[args.run]['hrefStartTL'],run[args.run]['hrefEndTL']+1),
        'uhThresh': 75,
        'pdt':'[7, 199, 2, 0, 116, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.2
    },
    '5':{
        'path': hrefDir,
        'name':['nmmb','conus.subset'],
        'run': hrefRun,
        'fHours': np.arange(run[args.run]['hrefStart'],run[args.run]['hrefEnd']+1),
        'uhThresh': 100,
        'pdt':'[7, 199, 2, 0, 112, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.2
    },
    '6':{
        'path': hrefDirTL,
        'name':['nmmb','conus.subset'],
        'run': hrefRunTL,
        'fHours': np.arange(run[args.run]['hrefStartTL'],run[args.run]['hrefEndTL']+1),
        'uhThresh': 100,
        'pdt':'[7, 199, 2, 0, 112, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.2
    },
    '7':{
        'path': hrrrDir,
        'name':['hrrr','wrfsfc'],
        'run': hrefRun,
        'fHours': np.arange(run[args.run]['hrefStart'],run[args.run]['hrefEnd']+1),
        'uhThresh': 75,
        'pdt':'[7, 199, 2, 0, 83, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.0
    },
    '8':{
        'path': hrrrDirTL,
        'name':['hrrr','wrfsfc'],
        'run': hrrrRunTL,
        'fHours': np.arange(run[args.run]['hrefStartTL']-6,run[args.run]['hrefEndTL']-5),
        'uhThresh': 75,
        'pdt':'[7, 199, 2, 0, 83, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.0
    },
    '9':{
        'path': namNestDir,
        'name':['nam','conusnest.hires'],
        'run': hrefRun,
        'fHours': np.arange(run[args.run]['hrefStart'],run[args.run]['hrefEnd']+1),
        'uhThresh': 100,
        'pdt':'[7, 199, 2, 0, 84, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.0
    },
    '10':{
        'path': namNestDirTL,
        'name':['nam','conusnest.hires'],
        'run': hrefRunTL,
        'fHours': np.arange(run[args.run]['hrefStartTL'],run[args.run]['hrefEndTL']+1),
        'uhThresh': 100,
        'pdt':'[7, 199, 2, 0, 84, 0, 0, 1, 23, 103, 0, 5000, 103, 0, 2000]',
        'dx': 3.0
    }
}

# override nmmb members if fv3 members are available
if fv3:
    hrefMembers['5']['name'][0] = 'fv3' 
    hrefMembers['5']['uhThresh'] = 200
    hrefMembers['6']['name'][0] = 'fv3' 
    hrefMembers['6']['uhThresh'] = 200

# SREF variables by hazard
gfunclist = {
    'caltor4':{
        'vars': ['sigtp1']
    },
    'calhail4':{
        'vars': ['hicapep1000', 'eshrp20']
    },
    'calwind4':{
        'vars': ['hicapep250', 'eshrp20']
    }
}

# function to exit script gracefully
def exitScript(msg):
    print(msg)
    end = datetime.datetime.utcnow()
    diff = (end - start).total_seconds()
    print('Run Time: ' + str(diff) + ' seconds')
    sys.exit()

# structure elements for computing neighborhood probabilities
struct = {
    '12':np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
       [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
       [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
       [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
       [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
       [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
       [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]),
    '13':np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
       [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
       [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
       [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
       [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
       [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
       [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
       [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])
}


# function for computing neighborhood UH >= pre-defined threshold 
def uhGrid(hrefFile, member, pdt):
    grbs = ng.Grib2Decode(hrefFile)
    lats, lons = grbs[1].latlons()
    for grb in grbs:
        if (grb.product_definition_template[0] == 7 and grb.product_definition_template[1] == 199 and grb.product_definition_template[2] == 2 and grb.product_definition_template[11] == 5000):
            uhVals = grb.data()
            break
    else:
        exitScript(f'FATAL ERROR: Updraft Helicity index not found in {hrefFile}, exiting...')

    hrefMembers[member]['lats'] = lats
    hrefMembers[member]['lons'] = lons
    roi = 40. / hrefMembers[member]['dx']
    hrefMembers[member]['roi'] = roi
    uhThresh = np.zeros(uhVals.shape)
    uhThresh[uhVals >= hrefMembers[member]['uhThresh']] = 1.
    uhThresh1 = binary_dilation(uhThresh,structure=struct[str(int(round(roi,0)))]).astype(uhThresh.dtype)
    return uhThresh1

# function that returns any valid 3-hourly SREF forecast hours within a previous 4-hour period
def getSREFHours(fcsth):
    fh2 = int(fcsth / 3.) * 3
    fh1 = fh2 - 3
    if fh1 < (fcsth - 4):
        fh1 = fh2
    return fh1, fh2

# parses data from gdlist text file and returns numpy array
def read_gdlist(f, mask=-9999):
    """

    :param f:
    :param mask:
    :return:
    """
    begin = False
    lonsize = None; latsize = None
    vals = []
    scale_factor = 1
    with open(f, "r") as IN:
        for line in IN:
            if not lonsize:
                if 'GRID SIZE' not in line: continue
                parts = line.split()
                parts = [p.strip() for p in parts]
                lonsize = int(parts[-2])
                latsize = int(parts[-1])
            if 'Scale factor' in line:
                scale_factor = 10**(float(line.split()[-1]))
            if 'ROW{:3d}'.format(latsize) in line or (begin and 'ROW' in line):
                begin = True
                val_tmp = line.split('ROW')[1].split()[1:]
            elif begin:
                val_tmp = line.split()
            else:
                continue
            for val in val_tmp:
                vals.append(scale_factor * float(val))
        vals = np.array(vals)
        if mask:
            vals = np.ma.masked_where(vals == mask, vals)
        vals = vals.reshape(latsize, -1)
    return vals[::-1]

# bin function
# Function that sorts probabilities into 11 bins.
# Pass function array of probabilities of certain variable.
def binhaz(arr):
    arr[arr<5] = 0
    arr[np.logical_and(arr>=5, arr<15)] = 10
    arr[np.logical_and(arr>=15, arr<25)] = 20
    arr[np.logical_and(arr>=25, arr<35)] = 30
    arr[np.logical_and(arr>=35, arr<45)] = 40
    arr[np.logical_and(arr>=45, arr<55)] = 50
    arr[np.logical_and(arr>=55, arr<65)] = 60
    arr[np.logical_and(arr>=65, arr<75)] = 70
    arr[np.logical_and(arr>=75, arr<85)] = 80
    arr[np.logical_and(arr>=85, arr<95)] = 90
    arr[arr>=95] = 100
    return (arr / 10).astype(int)

# bin function for full period calculations
def binhaz24(arr):
    arr[arr<2.5] = 0
    arr[np.logical_and(arr>=2.5, arr<7.5)] = 5
    arr[np.logical_and(arr>=7.5, arr<12.5)] = 10
    arr[np.logical_and(arr>=12.5, arr<17.5)] = 15
    arr[np.logical_and(arr>=17.5, arr<22.5)] = 20
    arr[np.logical_and(arr>=22.5, arr<27.5)] = 25
    arr[np.logical_and(arr>=27.5, arr<32.5)] = 30
    arr[np.logical_and(arr>=32.5, arr<37.5)] = 35
    arr[np.logical_and(arr>=37.5, arr<42.5)] = 40
    arr[np.logical_and(arr>=42.5, arr<47.5)] = 45
    arr[arr>=47.5] = 50
    return (arr / 5).astype(int)

def saveGRIB(data, eTime, now, fhour, hType, outTime, outGRIB):
    if type(data) is not list:
        data = [data]

    # Define msg codes
    if hType == 'tor':
        hTypeNum = 197
    elif hType == 'hail':
        hTypeNum = 198
    elif hType == 'wind':
        hTypeNum = 199

    if outTime == '4':
        sTime = eTime - datetime.timedelta(hours=4)
    elif args.run == '15':
        sTime = datetime.datetime(int(args.date[:4]),int(args.date[4:6]),int(args.date[6:8]),16)
        eTime = datetime.datetime(int(args.date[:4]),int(args.date[4:6]),int(args.date[6:8]),12) + datetime.timedelta(days=1)
    elif args.run == '21':
        sTime = datetime.datetime(int(args.date[:4]),int(args.date[4:6]),int(args.date[6:8]),12) + datetime.timedelta(days=1)
        eTime = sTime + datetime.timedelta(days=1)
    else:
        sTime = datetime.datetime(int(args.date[:4]),int(args.date[4:6]),int(args.date[6:8]),12)
        eTime = sTime + datetime.timedelta(days=1)
    
    idsect = np.array([7, 9, 1, 1, 1, now.year, now.month, now.day, now.hour, now.minute, now.second, 0, 1])
    gdsinfo = np.array([0, len(data[0].flatten()), 0, 0, 30])
    gdtmpl = np.array([6, 0, 0, 0, 0, 0, 0, 185, 129, 12190000, 226541000, 8, 25000000, 
                       265000000, 40635000, 40635000, 0, 64, 25000000, 25000000, 0, 0])
    pdtmpl = np.array([19, hTypeNum, 5, 0, 0, 0, 0, 1, fhour, 1, 0, 0, 255, 0, 0, 0, 21, 1, 0,
                       0, 0, 0, eTime.year, eTime.month, eTime.day, eTime.hour,
                       0, 0, 1, 0, 1, 2, 1, int(outTime), 255, 0])
    drtmpl = np.array([0, 0, 1, 10, 0, 0, 255])

    encoder = ng.Grib2Encode(0, idsect)
    encoder.addgrid(gdsinfo, gdtmpl)
    for forecast in data:
        encoder.addfield(9, pdtmpl, 40, drtmpl, forecast)
    encoder.end()

    # Save the file
    with open(outGRIB, 'wb') as f:
        f.write(encoder.msg)

def computeNeighborhoodProbs(uh, uhProbs, rTime):
    # compute forecast time
    forecastTime = rTime.strftime('%Y%m%d%H')
    print('Computing Neighborhood Probabilities: ' + forecastTime)

    # compute grid point probability
    uhProbGrid = np.average(np.array(uh), axis=0) * 100

    # Use astropy smoothing function to take into account NaNs.
    uhProbGrid[uhProbGrid < 0.] = np.nan

    # Smooth using astropy.convolve
    sigma = Gaussian2DKernel(x_stddev=hrefMembers['1']['roi'])

    uhProbGrid = convolve(uhProbGrid,sigma,preserve_nan=True)

    # Set NaNs to zero so calhits and caltots can handle array.
    wnan = np.isnan(uhProbGrid)
    uhProbGrid[wnan] = 0.

    # convert to SREF 80 km grid
    x1 = hrefMembers['1']['lons'].flatten()
    y1 = hrefMembers['1']['lats'].flatten()
    g3km = np.vstack((x1, y1)).T
    interpolator = NearestNDInterpolator(g3km, uhProbGrid.flatten())
    vals = []
    for j in range(len(srefX)):
        vals.append(interpolator(srefX[j],srefY[j]))
    uhProbGrid = np.array(vals).reshape(srefLons.shape)

    # store grid
    uhProbs[forecastTime] = uhProbGrid

    return uhProbs, rTime

sigma = Gaussian2DKernel(x_stddev=1)

cal4 = {'tor':[],'wind':[],'hail':[]}
def computeCal4(cal4, rTime2, now, idx, fhour):
    forecastTime = rTime2.strftime('%Y%m%d%H')
    srefFH1, srefFH2 = getSREFHours(run[args.run]['srefStart']+idx)
    srefFH1 = str(srefFH1).zfill(3)
    srefFH2 = str(srefFH2).zfill(3)
    fh = str(run[args.run]['srefStart']+idx).zfill(3)
    for gfunc in gfunclist:
        haz = gfunc[3:-1]
        if haz == 'tor':
            if srefFH1 != srefFH2:
                maxSREF = np.maximum(srefData[srefFH1][haz]['sigtp1'], srefData[srefFH2][haz]['sigtp1'])
            else:
                maxSREF = srefData[srefFH1][haz]['sigtp1']
        elif haz == 'hail' or haz == 'wind':
            if srefFH1 != srefFH2:
                maxCAPE = np.maximum(srefData[srefFH1][haz][gfunclist[gfunc]['vars'][0]], srefData[srefFH2][haz][gfunclist[gfunc]['vars'][0]])
                maxSHEAR = np.maximum(srefData[srefFH1][haz][gfunclist[gfunc]['vars'][1]], srefData[srefFH2][haz][gfunclist[gfunc]['vars'][1]])
            else:
                maxCAPE = srefData[srefFH1][haz][gfunclist[gfunc]['vars'][0]]
                maxSHEAR = srefData[srefFH1][haz][gfunclist[gfunc]['vars'][1]]
            maxSREF = (maxCAPE * maxSHEAR) / 100

        # Use astropy smoothing function to take into account NaNs.
        uhProbGrid = uhProbs[forecastTime]

        # Use bin function on numpy arrays of parameters.
        uhProbGridBinned = binhaz(uhProbGrid)
        maxSREFBinned = binhaz(maxSREF)

        # Load previously computed calibration table for forecast hour.
        x = np.load(fix_dir + '/cal_' + haz + '_tbl' + args.run + '_f' + fh[1:] + '.npz')

        caltbl = x['calib_table']
        if args.cap:
            if haz == 'tor' or haz == 'hail':
                caltbl[caltbl > 0.6] = 0.6
            elif haz == 'wind':
                caltbl[caltbl > 0.75] = 0.75

        # Create an empty dictionary for newly loaded caltbl
        cal_lookup_tbl = {}

        # Create keys for cal_lookup_tbl dictionary and assign values from caltbl to
        # appropriate key.
        for j in range(caltbl.shape[0]):
            for k in range(caltbl.shape[1]):
                cal_lookup_tbl[(j,k)] = caltbl[j,k]

        # Flatten both binned forecast parameter arrays.
        uhProbGridBinnedRav = uhProbGridBinned.ravel()
        maxSREFRav = maxSREFBinned.ravel()

        # Create an empty array for forecast probabilities.
        # Array is the same size as flattened forecast parameters.
        fcst = np.zeros(uhProbGridBinnedRav.shape)

        # Combine flattened parameter arrays into 1-D array.
        comb = zip(uhProbGridBinnedRav, maxSREFRav)

        # Loop through comb. For the selected value in comb, use that as the dictionary
        # key to grab the appropriate probability from the cal_look_up table. Place
        # this value into fcst.
        for i,c in enumerate(comb):
            fcst[i] = (cal_lookup_tbl[c]) *100

        # Reshape fcst into 129x185 array to plot on model grid.
        fcst = (fcst.reshape(uhProbGridBinned.shape))

        if fhour != "full":
            # write to grib2
            if args.run == '12' or args.run == '00':
                href_hour = int(fh) - 3
            elif args.run == '15' or args.run == '03':
                href_hour = fh
            href_hour = str(href_hour).zfill(3) 
            calFileGrib = grbDir + '/href_cal_' + haz + '.t' + args.run + 'z.4hr.f' + href_hour + '.grib2'
            saveGRIB(fcst, rTime2, now, int(href_hour) - 4, haz, '4', calFileGrib) 

        # add to dictionary for use in full period probability
        cal4[haz].append(fcst)

    rTime2 += datetime.timedelta(hours=1)
    return cal4, rTime2

# compute full period probabilities
def computeCalFull(cal4, now):
    for haz in cal4:
        agg = np.sum(cal4[haz][::4], axis=0)
        fmax = np.maximum.reduce(cal4[haz][::4])

        # Bin newly created arrays.
        aggbinned = binhaz24(agg)
        fmaxbinned = binhaz24(fmax)

        # Load previously computed calibration table for forecast hour.
        x = np.load(fix_dir + '/cal_' + haz + '_24h_tbl' + args.run + '.npz')

        caltbl = x['calib_table']
        if args.cap:
            if haz == 'tor' or haz == 'hail':
                caltbl[caltbl > 0.6] = 0.6
            elif haz == 'wind':
                caltbl[caltbl > 0.75] = 0.75

        # Create an empty dictionary for newly loaded caltbl
        cal_lookup_tbl = {}

        # Create keys for cal_lookup_tbl dictionary and assign values from caltbl
        # to appropriate key.
        for i in range(caltbl.shape[0]):
            for j in range(caltbl.shape[1]):
                cal_lookup_tbl[(i,j)] = caltbl[i,j]

        # Flatten both binned forecast parameter arrays.
        aggrav = aggbinned.ravel()
        fmaxrav = fmaxbinned.ravel()

        # Create an empty array for forecast probabilities.
        # Array is the same size as flattened forecast parameters.
        fcsttemp = np.zeros(aggrav.shape)

        # Combine flattened parameter arrays into 1-D array.
        comb = zip(aggrav,fmaxrav)

        # Loop through comb. For the selected value in comb, use that as the 
        # dictionary key to grab the appropriate probability from the cal_look_up
        # table. Place this value into fcst.
        for i,c in enumerate(comb):
            fcsttemp[i] = (cal_lookup_tbl[c])*100

        # Reshape fcst into 129x185 array to plot on model grid.
        fcsttemp = (fcsttemp.reshape(aggbinned.shape))

        # If any grid point in fcst array is lower than one of the used hours,
        # replace it with that hour.
        fcst = np.maximum.reduce([fcsttemp] + cal4[haz])

        # Call gemwrite function to write a GDLIST file for GEMPAK to use
        ngfunc = 'cal' + haz + '24'
        fh = str(run[args.run]['srefEnd']).zfill(3)

        # write to grib2
        if args.run == '12' or args.run == '00':
            href_hour = int(fh) - 3
        elif args.run == '15' or args.run == '03':
            href_hour = fh
        href_hour = str(href_hour).zfill(3)
        calFileGrib = grbDir + '/href_cal_' + haz + '.t' + args.run + 'z.24hr.f' + href_hour + '.grib2' 
        if args.run == '12' or args.run == '00' or args.run == '03':
            saveGRIB(fcst, rEnd, now, int(href_hour) - 24, haz, '24', calFileGrib)
        elif args.run == '15':
            saveGRIB(fcst, rEnd, now, int(href_hour) - 20, haz, '20', calFileGrib)

    return

# Main block of compute code starts here
# compute calibrated forecasts for each hazard
print('Extracting SREF data')
srefFiles = []
waiting = True
fCount = 0
while waiting:
    txt = ['#!/bin/csh','','$GEMEXE/gdlist <<EOF']
    notFound = False
    for i in range(min(getSREFHours(run[args.run]['srefStart'])),run[args.run]['srefEnd']+3,3):
        fh = str(i).zfill(3)
        for gfunc in gfunclist:
            for v in gfunclist[gfunc]['vars']:
                srefFile = srefDir + '/spcsref_' + srefRun + 'f' + fh
                print(srefFile)
                if srefFile in srefFiles:
                    continue
                elif not os.path.exists(srefFile):
                    notFound = True
                    break
                txt.append('')
                txt.append('    GDFILE   = ' + srefFile)
                txt.append('    GDATTIM  = ' + srefRun[2:8] + '/' + srefRun[-2:] + '00F' + fh)
                txt.append('    GLEVEL   = 0')
                txt.append('    GVCORD   = none')
                txt.append('    GFUNC    = ' + v)
                txt.append('    GAREA    = grid')
                txt.append('    PROJ     =')
                txt.append('    SCALE    = 0')
                txt.append('    OUTPUT   = f/' + tmpDir + '/sref_' + srefRun + '_' + v + '_' + fh + '.txt')
                txt.append('')
                txt.append('run')
        if notFound:
            fCount += 1
            if fCount > 60: # change if need be (60 minutes currently)
                exitScript('FATAL ERROR: Not enough SREF data available, exiting...')
            else:
                print('WARNING: Not enough SREF data available, waiting one minute.')
                time.sleep(60)
                break
    if not notFound:
        waiting = False
        break
txt.extend(['','exit','','EOF'])

# write gdlist commands to c-shell script and execute script
# this will create many text files containing SREF env data
with open(tmpDir + '/gdlist.csh','w') as fh:
    fh.write('\n'.join(txt))

os.chmod(tmpDir + '/gdlist.csh', 0o755)

p = Popen(tmpDir + '/gdlist.csh', shell=True, stdout=PIPE)
p.wait()

# read SREF env data to numpy arrays
print('Formatting SREF data')
srefData = {}
for i in range(min(getSREFHours(run[args.run]['srefStart'])),run[args.run]['srefEnd']+3,3):
    fh = str(i).zfill(3)
    srefData[fh] = {}
    print(fh)
    for gfunc in gfunclist:
        haz = gfunc[3:-1]
        srefData[fh][haz] = {}
        for v in gfunclist[gfunc]['vars']:
            gdListFile = tmpDir + '/sref_' + srefRun + '_' + v + '_' + fh + '.txt'
            if not os.path.exists(gdListFile):
                exitScript('FATAL ERROR: gdlist data file not available (' + gdListFile + '), exiting.')
            srefData[fh][haz][v] = read_gdlist(gdListFile)

# now extract hourly max UH from HREF grib2 data
# while remapping max values to the SREF 40km grid (neighborhooding)
print(args.fhour)
if not os.path.exists(uhProbsFile) and args.fhour != "full":
    print('Extracting UH and regridding HREF data for 4hr forecasts')
    uhProbs = {}
    uhGrids = {}
    uhGridsProcessed = {}
    waiting = True
    fCount = 0
    uh = []
    notFound = False
    while waiting:
        rTime = rTimeOrig 
        for i in range(len(hrefMembers['1']['fHours'])):
            for member in hrefMembers:
                if member not in uhGrids:
                    uhGrids[member] = []
                    uhGridsProcessed[member] = []
                if hrefMembers[member]['fHours'][i] in uhGridsProcessed[member]:
                    continue
                if hrefMembers[member]['name'][0] == 'hrrr':
                    hrefFile = hrefMembers[member]['path'] + '/hrrr.t' + hrefMembers[member]['run'][-2:] + 'z.wrfsfcf' + str(hrefMembers[member]['fHours'][i]).zfill(2) + '.grib2'
                elif hrefMembers[member]['name'][0] == 'nam':
                    hrefFile = hrefMembers[member]['path'] + '/nam.t' + hrefMembers[member]['run'][-2:] + 'z.conusnest.camfld' + str(hrefMembers[member]['fHours'][i]).zfill(2) + '.tm00.grib2'
                else:
                    hrefFile = hrefMembers[member]['path'] + '/hiresw.t' + hrefMembers[member]['run'][-2:] + 'z.' + hrefMembers[member]['name'][0] + '_3km.f' + str(hrefMembers[member]['fHours'][i]).zfill(2) + '.' + hrefMembers[member]['name'][1] + '.grib2'
                print(f'Loading {hrefFile}')
                if not os.path.exists(hrefFile):
                    print('Waiting one minute to find ' + hrefFile)
                    notFound = True
                    break
                uhGrids[member].append(uhGrid(hrefFile, member, hrefMembers[member]['pdt']))
                uhGridsProcessed[member].append(hrefMembers[member]['fHours'][i])
                if i >= 3:
                    max4hrUH = np.maximum.reduce([uhGrids[member][i], uhGrids[member][i-1], uhGrids[member][i-2], uhGrids[member][i-3]])
                    uh.append(max4hrUH)
            if notFound:
                break
            elif i >= 3:
                forecastTime = rTime.strftime('%Y%m%d%H')
                if forecastTime in uhProbs:
                    rTime += datetime.timedelta(hours=1)
                    continue
                uhProbs, rTime = computeNeighborhoodProbs(uh, uhProbs, rTime)
                rTime += datetime.timedelta(hours=1)
                uh = []
                idx = i-3
                cal4, rTime2 = computeCal4(cal4, rTime2, now, idx, args.fhour)
                forecastHour = rTime2.strftime('%H')
        if notFound:
            fCount += 1
            if fCount > 120: # change if need be, currently 2 hours of checking
                exitScript('FATAL ERROR: Not enough HREF members available to produce calibrated probabilities, exiting...')
            else:
                time.sleep(60)
                notFound = False
        else:
            waiting = False
            break

    # Save pickle file for use in 24 hr forecasts and in 15Z, 03Z updates
    with open(uhProbsFile, 'wb') as fh:
        pickle.dump(uhProbs, fh, protocol=pickle.HIGHEST_PROTOCOL)

elif args.fhour != "full":
    print('Loading Pre-Computed 4-hr UH Probabilities')
    with open(uhProbsFile, 'rb') as fh:
        uhProbs = pickle.load(fh)    

    print('Computing 4-hour Calibrated HREF/SREF Probabilities')
    for i in range(run[args.run]['srefStart'],run[args.run]['srefEnd']+1):
        idx = i - run[args.run]['srefStart']
        cal4, rTime2 = computeCal4(cal4, rTime2, now, idx, args.fhour)
elif args.fhour == "full":
    print('Loading Pre-Computed 4-hr UH Probabilities')
    with open(uhProbsFile_full, 'rb') as fh:
        uhProbs = pickle.load(fh)
    for i in range(run[args.run]['srefStart'],run[args.run]['srefEnd']+1):
        idx = i - run[args.run]['srefStart']
        cal4, rTime2 = computeCal4(cal4, rTime2, now, idx, args.fhour)
    print('Computing Day 1 Full Period Calibrated HREF/SREF Probabilities')
    computeCalFull(cal4, now)
exitScript('Done')

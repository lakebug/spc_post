#!/bin/sh

echo "============================================================="
echo "=                                                           ="
echo "= Start the HREF Calibrated Thunderstorm forecast for f`printf %03d ${fhour}`  ="
echo "=                                                           ="
echo "============================================================="

set -x

# get output file names
hour=`printf %03d ${fhour}`
if [ $hour -lt 4 ]
then 
    grib_files=("hrefct.t${cyc}z.thunder_1hr.f${hour}.grib2")
else
    grib_files=("hrefct.t${cyc}z.thunder_1hr.f${hour}.grib2" "hrefct.t${cyc}z.thunder_4hr.f${hour}.grib2")   
fi

# COLDSTART check
# Remove all existing grib2 files for current cycle if YES
if [ ${COLDSTART} == "YES" ]; then
    for grib_file in ${grib_files[@]}
    do
        if [ -f $COMOUTspc_post/thunder/${grib_file} ]; then
            echo "COLDSTART - removing $COMOUTspc_post/thunder/${grib_file}"
            rm $COMOUTspc_post/thunder/${grib_file}
        fi
    done
fi

# start forecast
python ${USHspc_post}/href_calib_thunder/forecast_href_cal_thunder.py ${fhour}
export err=$?; err_chk

# dbnet alerts
if [ "$SENDDBN" = 'YES' ]
then
    for grib_file in ${grib_files[@]}
    do
        echo "      Sending ${grib_file} to DBNET."
        $DBNROOT/bin/dbn_alert MODEL SPCPOST_THUNDER_GRIB $job $COMOUTspc_post/thunder/${grib_file}
    done
fi
exit 0

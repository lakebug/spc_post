#!/bin/sh

echo "============================================================="
echo "=                                                           ="
echo "=      Start the HREF Calibrated Thunderstorm forecast      ="
echo "=             Full Period Section $((${fhour}-48))                         ="
echo "=                                                           ="
echo "============================================================="

set -x

# get output file names
grib_files=()
fp_job=$((${fhour}-48))
if [ ${cyc} -eq 00 ]; then
    if [ ${fp_job} -eq 1 ]; then
        export start_fp=0 end_fp=11
    elif [ ${fp_job} -eq 2 ]; then
        export start_fp=12 end_fp=35
    else
        export start_fp=36 end_fp=47
    fi
else
    if [ ${fp_job} -eq 1 ]; then
        export start_fp=0 end_fp=23
    else
        export start_fp=24 end_fp=47
    fi
fi
for hour in `seq ${start_fp} ${end_fp}`
do
    fp_hour=`printf %03d ${hour}`
    grib_file="hrefct.t${cyc}z.thunder_full.f${fp_hour}.grib2"
    grib_files+=("${grib_file}")
done

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

#!/bin/sh

echo "============================================================="
echo "=                                                           ="
echo "=      Start the HREF/SREF Calibrated Severe forecast       ="
echo "=             for full period                               ="
echo "=                                                           ="
echo "============================================================="

set -x

# get output file names
grib_files=()
if [ $cyc == '00' ]; then fhour=036; cyc_tmp=$cyc; fi
if [ $cyc == '06' ]; then fhour=033; cyc_tmp=03; fi
if [ $cyc == '12' ]; then fhour=024; cyc_tmp=$cyc; fi
if [ $cyc == '18' ]; then fhour=021; cyc_tmp=15; fi
for domain in hail wind tor
do
    grib_file="href_cal_${domain}.t${cyc_tmp}z.24hr.f${fhour}.grib2"
    grib_files+=("${grib_file}")
done

# COLDSTART check
# Remove existing grib2 and pickcle files for current cycle if YES
if [ ${COLDSTART} == "YES" ]; then
    for grib_file in ${grib_files[@]}
    do
        if [ -f $COMOUTspc_post/severe/${grib_file} ]; then
            echo "COLDSTART - removing $COMOUTspc_post/severe/${grib_file}"
            rm $COMOUTspc_post/severe/${grib_file}
        fi
    done
    pickle_file="${COMOUTspc_post}/spc_pickle/uhProbs_${PDY}${cyc_tmp}.pickle"
    if [ -f ${pickle_file} ]; then
        echo "COLDSTART - removing ${pickle_file}"
        rm ${pickle_file}
    fi
fi


# start forecast
python $USHspc_post/href_calib_severe/launch_href_cal_severe.py "full"
export err=$?; err_chk

# dbnet alerts
if [ "$SENDDBN" = 'YES' ]
then
    for grib_file in ${grib_files[@]}
    do
        echo "      Sending ${grib_file} to DBNET."
        $DBNROOT/bin/dbn_alert MODEL SPCPOST_SEVERE_GRIB $job $COMOUTspc_post/severe/${grib_file}
    done
fi
exit 0

#!/bin/sh

echo "============================================================="
echo "=                                                           ="
echo "=      Start the HREF/SREF Calibrated Severe forecast       ="
echo "=             for f`printf %03d ${fhour}`                                      ="
echo "=                                                           ="
echo "============================================================="

set -x

fhour_pad=`printf %03d $fhour`

# get output file names
grib_files=()
if [ $cyc -eq 00 -o $cyc -eq 12 ]; then fhour_out=${fhour}; cyc_out=$cyc; fi
if [ $cyc -eq 06 ]; then fhour_out=$((${fhour}-3)); cyc_out=03; fi
if [ $cyc -eq 18 ]; then fhour_out=$((${fhour}-3)); cyc_out=15; fi
fhour_out=`printf %03d $fhour_out`
for domain in hail wind tor
do
    grib_file="href_cal_${domain}.t${cyc_out}z.4hr.f${fhour_out}.grib2"
    grib_files+=("${grib_file}")
done

# COLDSTART check
# Remove existing grib2 and pickle files for current cycle if YES
if [ ${COLDSTART} == "YES" ]; then
    for grib_file in ${grib_files[@]}
    do
        if [ -f $COMOUTspc_post/severe/${grib_file} ]; then
            echo "COLDSTART - removing $COMOUTspc_post/severe/${grib_file}"
            rm $COMOUTspc_post/severe/${grib_file}
        fi
    done
    if [ $cyc -eq 00 -o $cyc -eq 06 ]; then
        pickle_file="${COMOUTspc_post}/spc_pickle/uhProbs_${PDY}00f${fhour_pad}.pickle"
    else
        pickle_file="${COMOUTspc_post}/spc_pickle/uhProbs_${PDY}12f${fhour_pad}.pickle"
    fi
        if [ -f ${pickle_file} ]; then
            echo "COLDSTART - removing ${pickle_file}"
            rm ${pickle_file}
        fi
fi

# start forecast
python $USHspc_post/href_calib_severe/launch_href_cal_severe.py ${fhour_pad}
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

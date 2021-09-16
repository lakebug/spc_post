#!/bin/sh

# Program Name: SPC NAM Post Process
# Affiliation: NOAA/NWS/Storm Prediction Center
# Contacts: matthew.elliott@noaa.gov (703-887-2332 cell)
# Abstract: 
#           - SPC NAM post process part of SPC POST
#           - Retrieve 1-hr precip (APCP) from operational NAM nest using wgrib2
#           - Input into HREF Calibrated Thunder
#
# Usage:
#   Parameters:
#       forecasthour: forecast hour chunk to be processed (must be interval of 3...e.g., f03, f06, f09, ..., f60)
#   Input Files (operational NAM NEST):
#       nam.tHHz.conusnest.camfldFF.tm00.grib2
#   Output Files (subset of needed variables with 1-hr precip):
#       nam.tHHz.conusnest.camfldFF.tm00.grib2
#

set -x

# set variables
forecasthour=${1}
yyyymmdd=${PDY}
run=${cyc}

# set in/out directories
data_directory="${COMINnam}/nam.${yyyymmdd}/"
#preprocess_directory="${COMOUT}/spc_nam.${yyyymmdd}/"
preprocess_directory="${COMOUTspc_nam}/"

# set processing directories
forecasthour_pad=`printf %02d ${forecasthour}`
tmp_directory="${DATA}/href_calib_thunder/f${forecasthour_pad}/"
all_directory="${tmp_directory}nam_all/"
group_directory="${tmp_directory}nam_group/"

# set start/end forecast hours
fhour_end=${forecasthour}
if [ ${forecasthour} -eq 3 ]; then
    fhour_start=$[${fhour_end}-3]
    n=0
else
    fhour_start=$[${fhour_end}-2]
    n=1
fi

# create array of forecast hours
fhours=( $(seq ${fhour_start} ${fhour_end} ) )

# check if any forecast hours need to be processed
process=0
for hour in "${fhours[@]}"
do
    fhour=`printf %02d ${hour}`
    filename="nam.t${run}z.conusnest.camfld${fhour}.tm00.grib2"
    file=${data_directory}${filename}
    if [ ! -f "${preprocess_directory}${filename}" ]; then
        ((process++))
    # COLDSTART - remove existing grib2 files if YES
    elif [ ${COLDSTART} == "YES" ]; then
        echo "COLDSTART - removing ${preprocess_directory}${filename}"
        rm ${preprocess_directory}${filename}*
        ((process++))
    fi
done

# Process only if files (any in the chunk) are missing
if [ ${process} -ge 1 ]; then
    echo "Running on ${yyyymmdd} ${run}Z f${forecasthour_pad}"

    # create temp/storage directories
    mkdir -p ${preprocess_directory}
    mkdir -p ${all_directory}
    mkdir -p ${group_directory}

    # extract only the grib messages that are needed into seperate files
    for hour in "${fhours[@]}"
    do 
        fhour=`printf %02d ${hour}`
        filename="nam.t${run}z.conusnest.camfld${fhour}.tm00.grib2"
        file=${data_directory}${filename}
        ${WGRIB2} ${file} -s | egrep ':4LFTX:180-0 mb above ground:' | ${WGRIB2} -i ${file} -grib ${all_directory}/lftx_${filename}
        ${WGRIB2} ${file} -s | egrep ':APCP:surface:' | ${WGRIB2} -i ${file} -grib ${all_directory}/apcp_${filename}
        ${WGRIB2} ${file} -s | egrep 'REFD:4000 m above ground:' | ${WGRIB2} -i ${file} -grib ${all_directory}/z4km_${filename}
        ${WGRIB2} ${file} -s | egrep ':REFD:263 K level:' | ${WGRIB2} -i ${file} -grib ${all_directory}/zminus10_${filename}
    done           

    # combine the precip files back into 1 grib file for processing
    for hour in "${fhours[@]}"
    do
        fhour=`printf %02d ${hour}`
        cat "${all_directory}apcp_nam.t${run}z.conusnest.camfld${fhour}.tm00.grib2" >> ${group_directory}/apcp.grib2
    done

    # convert 3hr precip to 1 hr precip
    ${WGRIB2} -match 'APCP:' ${group_directory}/apcp.grib2 -vt | sort -t: -k3,3 | ${WGRIB2} -i ${group_directory}/apcp.grib2 -ncep_norm ${group_directory}/apcp_new.grib2

    # combine grib messages for each file back into 1 file and save in spc_nam.yyyymmdd
    for hour in "${fhours[@]}"
    do
        fhour=`printf %02d ${hour}`
        fname="nam.t${run}z.conusnest.camfld${fhour}.tm00.grib2"
        idx="${fname}.idx"
        ${WGRIB2} ${group_directory}/apcp_new.grib2 -match "(^$n:)" -grib ${all_directory}/precip_${fname}
        cat ${all_directory}/lftx_${fname} ${all_directory}/zminus10_${fname} ${all_directory}/z4km_${fname} ${all_directory}/precip_$fname > ${preprocess_directory}/${fname}
        ${WGRIB2} ${preprocess_directory}/${fname} > ${preprocess_directory}/${idx}
        ((n++))
    done
else
    echo "All files already processed for ${yyyymmdd} ${run}Z f${forecasthour_pad}"
fi


#!/bin/sh

# Program Name: SPCPOST HREF Calibrated Thunder Manager 
# Affiliation: NOAA/NWS/Storm Prediction Center
# Contacts: matthew.elliott@noaa.gov (703-887-2332 cell)
# Abstract: Launcher/Manager script for HREF  Calibrated Thunder part of SPC POST
#           Input into HREF Calibrated Thunder
#

set -x

# set directories
nam_directory="${COMOUTspc_nam}/"
hrrr_directory="${COMINhrrr}/hrrr.${PDY}/conus/"
hiresw_directory="${COMINhiresw}/hiresw.${PDY}/"
thunder_directory="${COMOUTspc_post}/thunder"

# COLDSTART check
# Remove all existing grib2 files for current cycle if YES
if [ ${COLDSTART} == "YES" ]; then
    echo "COLDSTART - removing ${thunder_directory}/hrefct.t${cyc}z.thunder*.grib2"
    rm ${thunder_directory}/hrefct.t${cyc}z.thunder*.grib2
fi

# initialize array (0 for not proccessed yet)
declare -a thunder_released=( $(for i in {1..48}; do echo 0; done) )
if [ ${cyc} -eq 12 ]; then
    declare -a fullperiod_released=( $(for i in {1..2}; do echo 0; done) )
    number_fp_required=2
elif [ ${cyc} -eq 00 ]; then
    declare -a fullperiod_released=( $(for i in {1..3}; do echo 0; done) )
    number_fp_required=3
fi
number_released=0
number_required=48
number_fp_released=0

echo "Running on $PDY ${cyc}Z"
while [ $number_released -ne $number_required ] || [[ $number_fp_released -ne $number_fp_required ]]
do
    for thunder_job in {1..48}
    do
        thunder_job_pad=`printf %02d $thunder_job`
        if [ ${thunder_released[$thunder_job-1]} -eq 0 ]; then
            echo "Checking files for thunder ${thunder_job}."
            fhour_end=$thunder_job
            if [ $thunder_job -le 3 ]; then
                fhour_start=$[$fhour_end-1]
            else
                fhour_start=$[$fhour_end-4]
            fi
 
            # get forecast hours needed for job
            fhours=( $(seq $fhour_start $fhour_end ) )
            sets_required="${#fhours[@]}"
            sets_available=0
         
            # run through each of the forecast hours and check if file is avialable
            for hour in "${fhours[@]}"
            do
                fhour=`printf %02d $hour`
                nam="${nam_directory}/nam.${cycle}.conusnest.camfld${fhour}.tm00.grib2.idx"
                hrrr="${hrrr_directory}/hrrr.${cycle}.wrfsfcf${fhour}.grib2.idx"
                nssl="${hiresw_directory}/hiresw.${cycle}.arw_3km.f${fhour}.conusmem2.subset.grib2.idx"
                arw="${hiresw_directory}/hiresw.${cycle}.arw_3km.f${fhour}.conus.subset.grib2.idx"
                hrw="${hiresw_directory}/hiresw.${cycle}.${COMINhrw_string}_3km.f${fhour}.conus.subset.grib2.idx"
                if [ -f $nam ] && [ -f $hrrr ] && [ -f $nssl ] && [ -f $arw ] && [ -f $hrw ]; then
                    echo " All f${fhour} files found for thunder_f${thunder_job_pad}."
                    ((sets_available++))
                else
                    echo " Waiting for f${fhour} files to arrive for thunder_f${thunder_job_pad}."
                fi
            done

            # if all sets available then release forecast hour for processing
            if [ $sets_available -eq $sets_required ]; then
                echo " ${sets_available} of ${sets_required} forecast hour files found for thunder${thunder_job_pad}! Releasing..."
                #!!!This is where it would release!!!
                ##### ecflow event set here #####
                ecflow_client --event release_thunder${thunder_job_pad}
                #################################
                echo " Released thunder_f${thunder_job_pad} at `date`."
                thunder_released[$thunder_job-1]=1
                ((number_released++))
                echo " Released $number_released of $number_required thunder fhours."
            fi
        fi
    done

    for fp_job in `seq 1 ${number_fp_required}`
    do
        if [ ${fullperiod_released[$fp_job-1]} -eq 0 ]; then
            fullperiod_release=0
            if [ ${cyc} -eq 00 ]; then
               if [ ${fp_job} -eq 1 ]; then
                  export start_4hr=4 end_4hr=12 start_fp=0
               elif [ ${fp_job} -eq 2 ]; then
                  export start_4hr=16 end_4hr=36 start_fp=12
               else
                  export start_4hr=40 end_4hr=48 start_fp=36
               fi
            else
               if [ ${fp_job} -eq 1 ]; then
                  export start_4hr=4 end_4hr=24 start_fp=0
               else 
                  export start_4hr=28 end_4hr=48 start_fp=24
               fi
            fi
            source ${USHspc_post}/href_calib_thunder/check_thunder_full.sh
            if [ ${fullperiod_release} -eq 1  ]; then
                fp_job_pad=`printf %02d $fp_job`
                ##### ecflow event set here #####
                ecflow_client --event release_thunder_full${fp_job_pad}
                #################################
                echo " Released full period ${fp_job_pad} at `date`."
                fullperiod_released[$fp_job-1]=1
                ((number_fp_released++))
            fi
        fi
    done

    if [ $number_released -ne $number_required ]|| [[ $number_fp_released -ne $number_fp_required ]]; then
        # if any of the thunder jobs have not been released then sleep and retry
        echo " Sleep 10 seconds before next round of check...zzz... `date | awk '{print $4}'`"
        sleep 10
    fi
done
echo " All 1/4 hour and full period jobs have been released. Exiting..."

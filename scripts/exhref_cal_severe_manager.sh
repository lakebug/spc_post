#!/bin/sh

# Program Name: SPCPOST HREF/SREF Calibrated Severe Manager 
# Affiliation: NOAA/NWS/Storm Prediction Center
# Contacts: matthew.elliott@noaa.gov (703-887-2332 cell)
# Abstract: Launcher/Manager script for HREF/SREF  Calibrated Severe part of SPC POST
#

set -x

# set directories

nam_directory="${COMINnam}/nam.${PDY}/"
hrrr_directory="${COMINhrrr}/hrrr.${PDY}/conus/"
hiresw_directory="${COMINhiresw}/hiresw.${PDY}/"
spc_post_severe="${COMOUTspc_post}/spc_pickle/"

# COLDSTART check
# Remove all existing grib2 and pickle files for current cycle if YES
if [ ${COLDSTART} == "YES" ]; then
    if [ $cyc -eq 00 -o $cyc -eq 12 ]; then cyc_tmp=$cyc; fi
    if [ $cyc -eq 06 ]; then cyc_tmp=03; fi
    if [ $cyc -eq 18 ]; then cyc_tmp=15; fi
    echo "COLDSTART - removing ${COMOUTspc_post}/severe/href_cal_*.t${cyc_tmp}z.*.grib2"
    rm ${COMOUTspc_post}/severe/href_cal_*.t${cyc_tmp}z.*.grib2
    if [ $cyc_tmp -eq 00 -o $cyc_tmp -eq 03 ]; then
        echo "COLDSTART - removing ${spc_post_severe}uhProbs_${PDY}00f*.pickle"
        rm ${spc_post_severe}uhProbs_${PDY}00*.pickle
    else
        echo "COLDSTART - removing ${spc_post_severe}uhProbs_${PDY}12f*.pickle"
        rm ${spc_post_severe}uhProbs_${PDY}12*.pickle
    fi
fi

sref_date=${PDY}
sref_files_required=9
num_jobs=21
if [ $cyc -eq 00 ]; then
   sref_date=${PDYm1}
   sref_run=21
   sref_start=15
   sref_end=39
   href_run="00"
   job_start=15
   job_dif=0
elif [ $cyc -eq 06 ]; then
   sref_run="03"
   sref_start=9
   sref_end=33
   href_run="00"
   job_start=15
   job_dif=3
elif [ $cyc -eq 12 ]; then
   sref_run="09"
   sref_start=3
   sref_end=27
   href_run="12"
   job_start=3
   job_dif=0
elif [ $cyc -eq 18 ]; then
   sref_run="15"
   sref_start=3
   sref_end=21
   sref_files_required=7
   href_run="12"
   job_start=7
   job_dif=3
   num_jobs=17
fi

declare -a severe_released=( $(for i in `seq 1 $num_jobs`; do echo 0; done) )

sref_directory="${COMINspcsref}/spcsref.${sref_date}/gempak/"
href_sets_required=4
number_released=0
number_fp_released=0
number_fp_required=1
sref_fp_files_required=$sref_files_required
echo "Running on $PDY ${cyc}Z"
while [ $number_released -ne $num_jobs ] || [ $number_fp_released -ne $number_fp_required ]
do
    # Check 4 hr forecasts
    for severe_job in `seq 1 $num_jobs`
    do
        if [ ${severe_released[$severe_job-1]} -eq 0 ]; then
            sref_released=0
            href_released=0
            valid_hour=$[$severe_job + $job_start]
            valid_hour_pad=`printf %03d ${valid_hour}`
            fcst_hour=$[$valid_hour - $job_dif]
            fcst_hour_pad=`printf %03d ${fcst_hour}`
            sref_files_available=0
            # Check sref files
            echo ""
            echo "Checking files needed for the $PDY ${cyc}Z f${fcst_hour_pad} forecast" 
            # Check sref files
            for forecast_hour in `seq ${sref_start} 3 ${sref_end}`
            do 
                forecast_hour_padded=`printf %03d ${forecast_hour}`
                echo "Checking for ${sref_date} ${sref_run}Z SREF f${forecast_hour_padded}"
                sref_file=${sref_directory}spcsref_${sref_date}${sref_run}f${forecast_hour_padded}
                if [ -f ${sref_file} ]; then
                    echo " f${forecast_hour_padded} file found for ${sref_run}Z SREF."
                    ((sref_files_available++))
                else
                    echo " Waiting for f${forecast_hour_padded} file to arrive for ${sref_run}Z SREF."
                fi
            done
            href_sets_available=0
            # Check for all href files
            href_start=$[${valid_hour} - 3]
            href_end=$valid_hour 
            for hour in `seq ${href_start} ${href_end}`
            do
                fhour=`printf %02d ${hour}`
                echo "Checking for ${PDY} ${href_run}Z HREF f${fhour}"
                nam="${nam_directory}/nam.t${href_run}z.conusnest.camfld${fhour}.tm00.grib2.idx"
                hrrr="${hrrr_directory}/hrrr.t${href_run}z.wrfsfcf${fhour}.grib2.idx"
                nssl="${hiresw_directory}/hiresw.t${href_run}z.arw_3km.f${fhour}.conusmem2.subset.grib2.idx"
                arw="${hiresw_directory}/hiresw.t${href_run}z.arw_3km.f${fhour}.conus.subset.grib2.idx"
                hrw="${hiresw_directory}/hiresw.t${href_run}z.${COMINhrw_string}_3km.f${fhour}.conus.subset.grib2.idx"
                if [ -f $nam ] && [ -f $hrrr ] && [ -f $nssl ] && [ -f $arw ] && [ -f $hrw ]; then
                    echo " f${fhour} files found for ${href_run}Z HREF."
                    ((href_sets_available++))
                else
                    echo " Waiting for f${fhour} files to arrive for ${href_run}Z HREF."
                fi
            done
            if [ $sref_files_available -eq $sref_files_required ]; then
                echo "All $sref_files_required required SREF files are available"
                sref_released=1
            else
                echo "$sref_files_available of $sref_files_required SREF files available"
            fi
            if [ $href_sets_available -eq $href_sets_required ]; then
                echo "All $href_sets_required required HREF sets are available"
                href_released=1
            else
                echo "$href_sets_available of $href_sets_required HREF sets available"
            fi
            if [ $sref_released -eq 1 ] && [ $href_released -eq 1 ]; then
                echo "All files are available for ${PDY} ${cyc}Z HREF/SREF Calibrated Severe f${fcst_hour_pad}! Releasing..."
                ##### ecflow event set here #####
                job_pad=`printf %02d $severe_job`
                ecflow_client --event release_severe${job_pad}
                #################################
                echo "Released ${PDY} ${cyc}Z HREF/SREF Calibrated Severe f${fcst_hour_pad} at `date`."
                severe_released[$severe_job-1]=1
                (( number_released++ ))
            fi
        fi
    done
    # Check full period forecast
    num_files=0
    if [ $number_fp_released -ne $number_fp_required ]; then
        if [ ${cyc} -eq 00 ] || [ ${cyc} -eq 06 ]; then
             export start_4hr=16 end_4hr=36 num_files_required=21 ahour=00
        elif [ ${cyc} -eq 12 ]; then
             export start_4hr=4 end_4hr=24 num_files_required=21 ahour=12
        elif [ ${cyc} -eq 18 ]; then
             export start_4hr=8 end_4hr=24 num_files_required=17 ahour=12
        fi
        echo ""
        echo "Checking files needed for the $PDY ${cyc}Z Full Period forecast" 
        # Check sref file dependencies
        sref_fp_files_available=0
        for forecast_hour in `seq ${sref_start} 3 ${sref_end}`
        do 
            forecast_hour_padded=`printf %03d ${forecast_hour}`
            sref_file=${sref_directory}spcsref_${sref_date}${sref_run}f${forecast_hour_padded}
            if [ -f ${sref_file} ]; then
                echo " f${forecast_hour_padded} file found for ${sref_run}Z SREF."
                ((sref_fp_files_available++))
            else
                echo " Waiting for f${forecast_hour_padded} file to arrive for ${sref_run}Z SREF."
            fi
        done
        # Check for 4hr pickle file dependencies
        for hour in `seq ${start_4hr} ${end_4hr}` 
        do
            fhour=`printf %03d ${hour}`
            spc_4hr_pickle_file=${spc_post_severe}uhProbs_${PDY}${ahour}f${fhour}.pickle
            if [ -f $spc_4hr_pickle_file ]; then
                echo "Found ${spc_4hr_pickle_file}"
                ((num_files++))
            fi
        done  
        echo "${num_files} of ${num_files_required} pickle files found!" 
        echo "${sref_fp_files_available} of ${sref_fp_files_required} sref files found!"
        if [ $num_files -eq $num_files_required ] && [ $sref_fp_files_available -eq $sref_fp_files_required ]; then
            echo "All files are available for ${PDY} ${cyc}Z HREF/SREF Calibrated Severe Full Period! Releasing..."
            ##### ecflow event set here #####
            ecflow_client --event release_severe_full
            #################################
            echo "Released ${PDY} ${cyc}Z HREF/SREF Calibrated Severe Full Period at `date`."
            number_fp_released=1
        else
            number_fp_released=0
        fi             
    fi
    if [ $number_released -ne $num_jobs ] || [ $number_fp_released -ne $number_fp_required ]; then
        echo ""
        echo "Released $number_released of $num_jobs 4hr jobs and $number_fp_released of $number_fp_required full period jobs."
        echo "Sleep 10 seconds before next round of check...zzz... `date | awk '{print $4}'`"
        sleep 10
    fi
done
echo "All 4 hour and full period jobs have been released. Exiting..."


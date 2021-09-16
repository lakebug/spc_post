#!/bin/sh
set -x
# This script checks 1/4 hr thunder files needed for full period jobs. 
# Inputs:
# start_4hr:                   4 ;   first forecast hour for 4 hr files
# end_4hr:                    12 ;   last forecast hour for 4 hr files
# start_fp:                    0 ;   first forecast hour for full period output

end_fp=$((${end_4hr}-1)) #    11 ;   last forecast hour for full period output
start_1hr=$((${end_4hr}-2)) # 10 ;   first forecast hour for 1 hr files
end_1hr=${end_4hr} #          12 ;   last forecast hour for 1 hr files

# check if all dependencies are meet
num_files=0
num_files_required=$((${end_4hr}-${start_4hr}+1))
echo "Checking files for full period: ${start_fp} to ${end_fp}"
for fcst_file in `seq ${start_4hr} ${end_4hr}`
do
    file_padded=`printf %03d $fcst_file`
    spc_4hr_file=${thunder_directory}/hrefct.${cycle}.thunder_4hr.f${file_padded}.grib2
    spc_1hr_file=${thunder_directory}/hrefct.${cycle}.thunder_1hr.f${file_padded}.grib2
    if [ $fcst_file -lt ${start_1hr} ]; then
        if [ -f $spc_4hr_file ]; then
            echo "Found ${spc_4hr_file}"
            ((num_files++))
        fi
    elif [ $fcst_file -ge ${start_1hr} ]; then
        if [ -f $spc_4hr_file ] && [ -f $spc_1hr_file ]; then
            echo "Found ${spc_4hr_file}"
            echo "Found ${spc_1hr_file}"
            ((num_files++))
        fi
    fi
done
echo "${num_files} of ${num_files_required} files found!"

# Release job if all dependencies are meet
if [ $num_files -eq $num_files_required ]; then
    fullperiod_release=1     
else
    fullperiod_release=0
fi

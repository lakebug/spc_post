#!/bin/bash
# Copy external calibration table files   

if [ "${SPCPOSTdir}" == "" ]
    then 
    echo "ERROR - Your SPCPOSTdir variable is not set"
    exit 1
fi

echo "Fetching externals...to ${SPCPOSTdir}/fix"

scp -r /gpfs/dell2/spc/noscrub/spc_post.v1.0.0/fix/* ${SPCPOSTdir}/fix/

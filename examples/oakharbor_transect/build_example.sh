#!/usr/bin/env bash
if [ -z "${USE_ATS}" ]; then
    echo "Set USE_ATS prior to running the build_example script"
    exit 1
fi

if [ ! -v NTASKS ]; then
    echo "Setting NTASKS = 1"
    NTASKS=1
fi


NTASKS=${NTASKS} \
      CASE_NAME=oakharbor_transect.np${NTASKS} \
      ATS_CASE_NAME=oakharbor_transect \
      INPUTDATA_NAME=5x1pt_Oakharbor \
      DOMAIN_NAME=oakharbor_transect_flat \
      ../build_example.sh


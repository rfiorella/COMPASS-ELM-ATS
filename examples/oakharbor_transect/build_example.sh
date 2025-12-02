#!/usr/bin/env bash
if [ -z "${USE_ATS}" ]; then
    echo "Set USE_ATS prior to running the build_example script"
    exit 1
fi

if [ ! -v NTASKS ]; then
    echo "Setting NTASKS = 1"
    NTASKS=1
fi


NTASKS=${NTASKS} CASE_NAME=oakharbor_transect_np${NTASKS} INPUTDATA_NAME=Oakharbor ../build_example.sh


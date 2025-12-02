#!/usr/bin/env bash
if [ -z "${USE_ATS}" ]; then
    echo "Set USE_ATS prior to running the build_example script"
    exit 1
fi

CASE_NAME=oakharbor_bare_column DOMAIN_NAME=oakharbor_column ATS_CASE_NAME=oakharbor_column INPUTDATA_NAME=1x1pt_Oakharbor ../build_example.sh

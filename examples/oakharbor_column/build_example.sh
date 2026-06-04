#!/usr/bin/env bash
if [ -z "${USE_ATS}" ]; then
    echo "Set USE_ATS prior to running the build_example script"
    exit 1
fi

CASE_NAME=oakharbor_column \
      INPUTDATA_NAME=1x1pt_Oakharbor \
      DOMAIN_FILE=domain.lnd.oakharbor_column.nc \
      SURF_DATA_FILE=surfdata_oakharbor_column.nc \
      ../build_example.sh

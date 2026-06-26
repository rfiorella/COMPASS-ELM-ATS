#!/usr/bin/env bash
if [ -z "${USE_ATS}" ]; then
    echo "Set USE_ATS prior to running the build_example script"
    exit 1
fi

if [ -z "${NTASKS}" ]; then
    echo "Setting NTASKS = 1"
    NTASKS=1
fi

NTASKS=${NTASKS} \
      CASE_NAME=oakharbor_transect_flat.np${NTASKS} \
      ATS_CASE_NAME=oakharbor_transect_flat \
      INPUTDATA_NAME=5x1pt_Oakharbor \
      DOMAIN_NAME=oakharbor_transect_flat \
      DOMAIN_FILE=domain.lnd.oakharbor_transect_flat.nc \
      SURF_DATA_FILE=surfdata_oakharbor_transect_flat.nc \
      ../build_example.sh


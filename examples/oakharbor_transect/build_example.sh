#!/usr/bin/env bash
if [ -z "${USE_ATS}" ]; then
    echo "Set USE_ATS prior to running the build_example script"
    exit 1
fi

if [ ! -v NTASKS ]; then
    echo "Setting NTASKS = 1"
    NTASKS=1
fi

# some options here:
# DOMAIN_NAME:
#  - oakharbor_transect.exo is the normal transect
#  - oakharbor_transect_flat.exo flat transect
# DOMAIN_FILE:
#  - domain.lnd.5x1pt_Oakharbor-GRID_navy.nc is the standard one
#  - domain.lnd.5x1pt_Oakharbor-GRID_navy_elmats.nc is set with identical lat-lon throughout so that forcing is identical

NTASKS=${NTASKS} \
      CASE_NAME=oakharbor_transect.np${NTASKS} \
      ATS_CASE_NAME=oakharbor_transect \
      INPUTDATA_NAME=5x1pt_Oakharbor \
      DOMAIN_NAME=oakharbor_transect \
      DOMAIN_FILE=domain.lnd.5x1pt_Oakharbor-GRID_navy_elmats.nc \
      ../build_example.sh


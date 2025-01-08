# Building prototype ELM-ATS:

[![Build Docker Image](https://github.com/amanzi/COMPASS-ELM-ATS/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/amanzi/COMPASS-ELM-ATS/actions/workflows/docker-ci.yml)

ELM-ATS should build from the head of ATS master branch, and against
the E3SM commit in the linked submodule. Two options to test/build the stack:

A) The image created by CI works now! So: `docker run -it metsi/compass-elm-ats:latest` and then can follow the general workflow in the ci.yml file to setup and build the case.

B) If wanting to build on ubuntu/mac locally:

1) `git clone --recurse-submodules -b rfiorella/initial-ci git@github.com:amanzi/COMPASS-ELM-ATS`
2) If building locally, need copy of Amanzi-ATS repo
3) Build TPLS as normal
4) Build ATS using `--enable-elm_ats_api` in bootstrap
5) (optional) if building on a machine not supported by E3SM, you'll need to update cmake files for E3SM. Examples are provided in cime_files in this repo for how these were configured for the docker machine. Typically they get placed in ~/.cime or /.cime if they are not part of the E3SM repo (in the container, they are in both locations). 
6) `cd E3SM/cime/scripts`
7) set up a new case - following steps provide an example using the GCREW transect: `./create_newcase --mach {machine_name} --res ELM_USRDAT --compset ICB20TRCNPRDCTCBC --case {CASE_DIR}`
8) `cd {CASE_DIR}`
9) Ultimately this should be a step that is done by the CIME case scripts, but for now, it's important that a variable ATS_DIR is set (i.e., ${ATS_DIR}/bin, ${ATS_DIR}/lib, ${ATS_DIR}/include exist and contain relevant ATS files)
10) `./case.setup`
11) `./case.build`
12) Need a folder that describes where E3SM holds inputdata - i.e., $DIN_LOC_ROOT in the config_machines.xml from step 5
13) Changes needed to user_nl_elm to run this case - user_nl_elm should contain at least (assuming we are using the coupler bypass as above compset indicates):
```
metdata_type = 'gswp3'
metdata_bypass = '$DIN_LOC_ROOT/atm/datm7/atm_forcing.datm7.GSWP3.0.5d.v2.c180716_US-GC03-GRID/cpl_bypass_full'
fsurdat = '$DIN_LOC_ROOT/lnd/clm2/surfdata_map/surfdata_110x1pt_US-GC_TransTEMPEST_c20230901.nc'

use_ats = .true.
ats_inputdir = '$DIN_LOC_ROOT/lnd/clm2/ats'
ats_inputfile = 'column_elm4ats.xml'
```
14) `./case.submit`

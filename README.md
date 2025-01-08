# Building prototype ELM-ATS:

[![Build Docker Image](https://github.com/amanzi/COMPASS-ELM-ATS/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/amanzi/COMPASS-ELM-ATS/actions/workflows/docker-ci.yml)

ELM-ATS should build from the head of ATS master branch, and against
the E3SM commit in the linked submodule. Two options to test/build the stack:

## Docker
The image created by CI works now! So: `docker run -it metsi/compass-elm-ats:latest` and then can follow the general workflow in the ci.yml file to setup and build the case.

## Local Builds
If wanting to build on ubuntu/mac locally:

0) set up directory structure and environmental variables for using E3SM .... (ADD MORE HERE)
1) make sure you have dependencies:
   - Perl LibXML: `sudo apt-get install libxml-libxml-perl`
   - MPI:
   - blas/lapack-dev
   - libcurl-dev: `sudo apt-get install libcurl4-gnutls-dev`
2) `git clone --recurse-submodules -b rfiorella/initial-ci git@github.com:amanzi/COMPASS-ELM-ATS ${ELM_ATS_SRC_DIR}`
3) `git clone git@github.com:rfiorella/pt-e3sm-inputdata ${E3SM_INPUTDATA_DIR}`  Unpack the inputdata files: `cd ${E3SM_INPUT_DATA}; . unpack.sh`
4) If building locally, need copy of Amanzi-ATS repo
5) Build TPLS as normal
6) Build ATS using `--enable-elm_ats_api` in bootstrap.  Make sure to follow standard ATS conventions, e.g. defining an ATS_DIR environmental variable.
7) FIX amanzi/amanzi#886 --- but until then, hack `$AMANZI_TPLS_DIR/lib/AmanziImportedTargets.cmake` to protect the netcdf section with: `IF (NOT TARGET netcdf) ... ENDIF`
8) (optional) If building on a machine not supported by E3SM, you'll need to update cmake files for E3SM. Examples are provided in cime_files in this repo for how these were configured for the docker machine. Typically they get placed in ~/.cime or /.cime if they are not part of the E3SM repo (in the container, they are in both locations).
  - `mkdir ~/.cime`
  - `cp COMPASS-ELM-ATS/cime_files/config_machines.xml ~/.cime`
  - `cp COMPASS-ELM-ATS/gnu_docker-ats.cmake ~/.cime/COMPILER_MACHINENAME.cmake`
  - edit `~/.cime/config_machines.xml`, adding an entry for MACHINENAME based on one of the existing machines.
 
8) `cd ${ELM_ATS_SRC_DIR}/E3SM/cime/scripts`
9) set up a new case - following steps provide an example using the GCREW transect: `./create_newcase --mach {machine_name} --res ELM_USRDAT --compset ICB20TRCNPRDCTCBC --case {CASE_DIR}`
10) `cd {CASE_DIR}`
11) `. ${ELM_ATS_SRC_DIR}/scripts/xmlchange_elm_ats.sh`
12) `./case.setup`
13) `./case.build`
14) Need a folder that describes where E3SM holds inputdata - i.e., $DIN_LOC_ROOT in the config_machines.xml from step 5
15) Changes needed to user_nl_elm to run this case - user_nl_elm should contain at least (assuming we are using the coupler bypass as above compset indicates):
```
metdata_type = 'gswp3'
metdata_bypass = '$DIN_LOC_ROOT/atm/datm7/atm_forcing.datm7.GSWP3.0.5d.v2.c180716_US-GC03-GRID/cpl_bypass_full'
fsurdat = '$DIN_LOC_ROOT/lnd/clm2/surfdata_map/surfdata_110x1pt_US-GC_TransTEMPEST_c20230901.nc'

use_ats = .true.
ats_inputdir = '$DIN_LOC_ROOT/lnd/clm2/ats'
ats_inputfile = 'column_elm4ats.xml'
```
16) `./case.submit`

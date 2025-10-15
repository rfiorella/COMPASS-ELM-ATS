# Building prototype ELM-ATS:

[![Build Docker Image](https://github.com/amanzi/COMPASS-ELM-ATS/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/amanzi/COMPASS-ELM-ATS/actions/workflows/docker-ci.yml)

ELM-ATS should build from the head of ATS master branch, and against
the E3SM commit in the linked submodule. Two options to test/build the stack:

## Docker
~~The image created by CI works now! So: `docker run -it metsi/compass-elm-ats:latest` and then can follow the general workflow in the ci.yml file to setup and build the case.~~ Current debugging progress:

Steps if using docker but not the CI image (e.g., Apple Silicon):
a) Clone this repo, then cd Docker; ./deploy-ats-elm-docker.sh
b) from top level repo directory: docker run -it -e E3SM_WORK_DIR=/home/amanzi_user/work -e ELM_ATS_SRC_DIR=/home/amanzi_user/E3SM -e MACHINE_NAME=docker-ats -e COMPILER_NAME=gnu -v $(pwd):/home/amanzi_user/compass -e HOME=/home/amanzi_user metsi/ats:elm_api (or, whatever tag was specified in deploy script from a)
c) . scripts/get_inputdata.x
d) . inputdata/unpack.sh
e) cd compass/examples
f) odd thing in E3SM currently seems to require that git config user.name and user.email are set. I have 
just been manually setting these at this point:
```
git config --global user.name "tester"
git config --global user.email "test@dev.null"
```
g) Oak Harbor ELM only test - worked for me as of 9/23/25
h) Oak Harbor ELM-ATS test - 

Common issues:
- NC_FillValue errors in build log - `$ELM_ATS_SRC_DIR` is pointing to out-of-date E3SM version.
- "No machine docker-ats found" - is `$HOME` set to `/home/amanzi_user`?


## Local Builds
If wanting to build on ubuntu/mac locally:

0) set up directory structure and environmental variables for using E3SM .... (ADD MORE HERE)
1) make sure you have dependencies:
   - Perl LibXML: `sudo apt-get install libxml-libxml-perl`
   - MPI:
   - blas/lapack-dev
   - libcurl-dev: `sudo apt-get install libcurl4-gnutls-dev`
2) `git clone --recurse-submodules -b rfiorella/initial-ci git@github.com:amanzi/COMPASS-ELM-ATS ${ELM_ATS_SRC_DIR}`
3) `git clone git@github.com:rfiorella/pt-e3sm-inputdata ${E3SM_WORK_DIR}/inputdata`  Unpack the inputdata files: `cd ${E3SM_WORK_DIR}/inputdata; . unpack.sh`
4) If building locally, need copy of Amanzi-ATS repo
5) Build TPLS as normal
6) Build ATS using `--enable-elm_ats_api` in bootstrap.  Make sure to follow standard ATS conventions, e.g. defining an ATS_DIR environmental variable.
7) FIX amanzi/amanzi#886 --- but until then, hack `$AMANZI_TPLS_DIR/lib/AmanziImportedTargets.cmake` to protect the netcdf section with: `IF (NOT TARGET netcdf) ... ENDIF`
8) (optional) If building on a machine not supported by E3SM, you'll need to update cmake files for E3SM. Examples are provided in cime_files in this repo for how these were configured for the docker machine. Typically they get placed in ~/.cime or /.cime if they are not part of the E3SM repo (in the container, they are in both locations).
  - `mkdir ~/.cime`
  - `cp COMPASS-ELM-ATS/cime_files/config_machines.xml ~/.cime`
  - `cp COMPASS-ELM-ATS/gnu_docker-ats.cmake ~/.cime/COMPILER_MACHINENAME.cmake`
  - edit `~/.cime/config_machines.xml`, adding an entry for MACHINENAME based on one of the existing machines.
 
9) `cd ${ELM_ATS_SRC_DIR}/E3SM/cime/scripts`
10) set up a new case - following steps provide an example using the GCREW transect: `./create_newcase --mach {machine_name} --res ELM_USRDAT --compset ICB20TRCNPRDCTCBC --case ${E3SM_WORK_CASE_DIR}`
11) `cd {CASE_DIR}`
12) `. ${ELM_ATS_SRC_DIR}/scripts/xmlchange_elm_only.sh`
13) `./case.build`
14) `./case.submit`

# Setting up and running a case with ATS

Effectively this follows from step 9 above, but with changes

1) cd into ${ELM_ATS_SRC_DIR}/E3SM/cime/scripts and create the case: `./create_newcase --mach {machine_name} --res ELM_USRDAT --compset ICB20TRCNPRDCTCBC --case ${E3SM_WORK_DIR}/cases/CASE_NAME`
2) Copy the xmlchange_elm_ats.sh file into your case directory and modify it with the correct input files (set up the case, see e.g. ats_demos/....! WIP): `cp ${ELM_ATS_SRC_DIR}/scripts/xmlchange_elm_ats.sh ${E3SM_WORK_DIR}/cases/CASE_NAME/`, then run it: `. xmlchange_elm_ats.sh`
3) Edit the file `${E3SM_WORK_DIR}/inputdata/lnd/clm2/ats/*_elm4ats.xml` file you named above, getting mesh paths right.
4) `./case.build`
5) `./case.submit`

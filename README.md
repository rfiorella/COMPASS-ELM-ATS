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
To build locally on a Mac or Linux machine, follow the following steps.

### Precursors

0) Set environmental variables for using ELM+ATS.
   - `ELM_ATS_SRC_DIR` = path to where you will clone this repository
   - Set standard ATS environmental variables:
      - `export AMANZI_SRC_DIR=${ELM_ATS_SRC_DIR}/amanzi`
      - `export ATS_SRC_DIR=${ELM_ATS_SRC_DIR}/amanzi/src/physics/ats`
      - Set `AMANZI_TPLS_DIR` and `AMANZI_TPLS_BUILD_DIR` as for standard Amanzi-ATS TPL installations.
      - Set `AMANZI_DIR` and `AMANZI_BUILD_DIR` as for standard Amanzi-ATS installations.
   - Set standard E3SM environmental variables:
      - `export E3SM_SRC_DIR=${ELM_ATS_SRC_DIR}/E3SM`
      - `MACHINE_NAME` and `COMPILER_NAME` -- set your machine and compiler (likely gnu) names -- see later steps for how this is used
      - Set an `E3SM_WORK_DIR` where you will place cases/builds/runs.

1) make sure you have dependencies (or their homebrew equivalents):
   - Perl LibXML: `sudo apt-get install libxml-libxml-perl`
   - MPI: `sudo apt-get install openmpi-dev`
   - blas/lapack-dev `sudo apt-get install libblas-dev liblapack-dev`
   - libcurl-dev: `sudo apt-get install libcurl4-gnutls-dev`
   
2) `git clone --recurse-submodules git@github.com:amanzi/COMPASS-ELM-ATS ${ELM_ATS_SRC_DIR}`
3) `git clone -b compass-glm git@github.com:rfiorella/pt-e3sm-inputdata ${E3SM_WORK_DIR}/inputdata`  Unpack the inputdata files: `cd ${E3SM_WORK_DIR}/inputdata; . unpack.sh`
4) Build Amanzi TPLs as normal (using bootstrap).
5) Build ATS using `--enable-elm_ats_api` in bootstrap.
6) FIX amanzi/amanzi#886 --- but until then, hack `$AMANZI_DIR/lib/AmanziImportedTargets.cmake` to protect the netcdf section with: `IF (NOT TARGET netcdf) ... ENDIF`
7) (optional) If building on a machine not supported by E3SM, you'll need to update cmake files for E3SM. Examples are provided in cime_files in this repo for how these were configured for the docker machine. Typically they get placed in ~/.cime or /.cime if they are not part of the E3SM repo (in the container, they are in both locations).
  - `mkdir ~/.cime`
  - `cp COMPASS-ELM-ATS/cime_files/config_machines.xml ~/.cime`
  - `cp COMPASS-ELM-ATS/gnu_docker-ats.cmake ~/.cime/${COMPILER_NAME}_${MACHINE_NAME}.cmake`
  - edit `~/.cime/config_machines.xml`, adding an entry for `$MACHINE_NAME` based on one of the existing machines.
 

### Create and build the new case.

Follow the examples:

0) `cd ${ELM_ATS_SRC_DIR}/examples/EXAMPLE_NAME`
1) Run the enclosed script `./build_example.sh` which creates the new case and calls case.setup and case.build.
2) Follow the on-screen instructions to run the case: `cd ${CASE_DIR} && ./case.submit`


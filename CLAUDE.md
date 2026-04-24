# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

COMPASS-ELM-ATS is a prototype coupling the **E3SM Land Model (ELM)** with the **Advanced Terrestrial Simulator (ATS)** subsurface hydrology model. The coupling allows ELM to use ATS for more sophisticated subsurface flow physics instead of ELM's native Richards equation solver.

**Architecture:**
- `E3SM/` - E3SM climate model (submodule), specifically the ELM land component
- `amanzi/` - Amanzi subsurface flow framework (submodule)
  - `amanzi/src/physics/ats/` - ATS physics packages
- `examples/` - Test cases demonstrating ELM-ATS coupling
- `inputdata/` - ELM input datasets for example cases
- `cime_files/` - CIME configuration for custom machines (e.g., docker)

## Environment Setup

Before building or running, these environment variables must be set:

```bash
# Top-level paths
export ELM_ATS_SRC_DIR=/path/to/COMPASS-ELM-ATS
export E3SM_WORK_DIR=/path/to/work  # for cases/builds/runs

# E3SM/CIME variables
export E3SM_SRC_DIR=${ELM_ATS_SRC_DIR}/E3SM
export MACHINE_NAME=<your-machine>  # e.g., docker-ats, mac
export COMPILER_NAME=gnu  # or intel

# Amanzi/ATS variables
export AMANZI_SRC_DIR=${ELM_ATS_SRC_DIR}/amanzi
export ATS_SRC_DIR=${ELM_ATS_SRC_DIR}/amanzi/src/physics/ats
export AMANZI_TPLS_DIR=/path/to/amanzi-tpls
export AMANZI_TPLS_BUILD_DIR=/path/to/amanzi-tpls-build
export AMANZI_DIR=/path/to/amanzi-install
export AMANZI_BUILD_DIR=/path/to/amanzi-build
```

## Building the Stack

### Docker Workflow (Recommended for Apple Silicon)

```bash
# 1. Build docker image
cd Docker
./deploy-ats-elm-docker.sh

# 2. Run container
cd ..
docker run -it --user=amanzi_user \
  -e E3SM_WORK_DIR=/home/amanzi_user/work \
  -e ELM_ATS_SRC_DIR=/home/amanzi_user/compass \
  -e MACHINE_NAME=docker-ats -e COMPILER_NAME=gnu \
  -v $(pwd):/home/amanzi_user/compass \
  metsi/ats:elm_api

# 3. Inside container, set git config (required by E3SM)
git config --global user.name "tester"
git config --global user.email "test@dev.null"
```

Or use the Makefile shortcut: `make ELM-ATS-debug`

### Local Build Workflow

**Prerequisites:** Perl LibXML, MPI (OpenMPI), BLAS/LAPACK, libcurl

1. Clone with submodules: `git clone --recurse-submodules git@github.com:amanzi/COMPASS-ELM-ATS ${ELM_ATS_SRC_DIR}`
2. Clone inputdata: `git clone -b compass-glm git@github.com:rfiorella/pt-e3sm-inputdata ${E3SM_WORK_DIR}/inputdata && cd ${E3SM_WORK_DIR}/inputdata && . unpack.sh`
3. Build Amanzi TPLs (using bootstrap)
4. Build ATS with `--enable-elm_ats_api` in bootstrap
5. **Workaround for amanzi#886:** Edit `$AMANZI_DIR/lib/AmanziImportedTargets.cmake` to wrap netcdf section in `IF (NOT TARGET netcdf) ... ENDIF`
6. If on unsupported machine: Copy `cime_files/config_machines.xml` and `cime_files/gnu_docker-ats.cmake` to `~/.cime/`

## Running Examples

Examples live in `examples/` with shared resources in `examples/shared/`.

**Example types:**
- Column examples: Single column simulations (e.g., `oakharbor_column`)
- Transect examples: 2D transects (e.g., `oakharbor_transect`)
- 3D examples: Full 3D domains (WIP)

**Run modes controlled by `USE_ATS` variable:**
- `USE_ATS=FALSE` - Native ELM only
- `USE_ATS=IC_ONLY` - ELM with ATS initial condition (for comparison)
- `USE_ATS=TRUE` - Full ELM+ATS coupling

### Standard Workflow

```bash
cd examples/<example_name>
USE_ATS=<TRUE|IC_ONLY|FALSE> ./build_example.sh

# Follow on-screen instructions, typically:
cd ${E3SM_WORK_DIR}/cases/<case_name>.<suffix>
./case.submit
```

The `build_example.sh` script:
1. Calls E3SM's `create_newcase` with custom resolution (`ELM_USRDAT`)
2. Configures the case (domain files, namelists, ATS XML if needed)
3. Runs `case.setup` and `case.build`

### Running ATS Standalone

For debugging ATS configuration without E3SM:

```bash
cd examples/shared
ats --xml_file=<example>.xml
```

## Key Configuration Files

**For each example:**
- `build_example.sh` - Sets `CASE_NAME` and `INPUTDATA_NAME`, calls parent script
- `user_nl_elm` - ELM namelist modifications
- `<example>.xml` - ATS input file (in example dir or `shared/`)

**ATS XML variants in `shared/`:**
- `oakharbor_column.xml` - Original (fails at month 18)
- `oakharbor_column_subcycle.xml` - Simple subcycling wrapper (recommended for single column)
- `oakharbor_column_opsplit.xml` - Operator split with subcycling (for multi-column)
- See `shared/QUICKSTART.md` and `shared/APPROACH_COMPARISON.md` for subcycling details

## Common Development Commands

### Testing/Comparison

```bash
# Run all cases for comparison
cd examples
./run_all_cases.sh

# Compare simulation results
python compare_simulations.py

# Plot water balance
python plot_water_balance.py
```

### Validation

```bash
# Validate ATS XML syntax
xmllint --noout examples/shared/<example>.xml

# Validate surface file
python scripts/validate_surfacefile.py <surface_file.nc>
```

### Debugging Container

```bash
# Enter debug container with current code
make ELM-ATS-debug

# Inside container, reproduce issue
cd compass/examples/oakharbor_column
USE_ATS=TRUE ./build_example.sh
cd /home/amanzi_user/work/cases/oakharbor_column.elm-ats
./case.submit
```

## Architecture Notes

### ELM-ATS Coupling Mechanism

**Flow of control:**
1. ELM computes surface energy balance, determines transpiration demand
2. ELM passes soil moisture fluxes to ATS via API
3. ATS solves Richards equation for subsurface pressure/saturation
4. ATS returns updated soil moisture to ELM
5. ELM continues with biogeochemistry, carbon cycle

**Key coupling variables:**
- `btran` - Transpiration wetness factor (0-1), controls water stress
- Soil water potential - Drives ATS Richards equation
- Soil moisture - Returned from ATS to ELM

**Timestep management:**
- ELM typically runs at 30-minute timesteps
- ATS may need to subcycle with smaller timesteps for stability
- Use subcycling MPCs in ATS XML to allow adaptive timesteps within ELM intervals

### MPC Types for Subcycling

**For single column:**
- `subcycling MPC` - Simple wrapper, subcycles entire coupled system
- Easy to configure, good for initial testing

**For multi-column:**
- `operator split coupled water` - Separates lateral (star system) from vertical (primary system)
- Star system: Lateral surface flow, runs once per ELM step
- Primary system: Vertical coupling with subcycling
- Required for good multi-column performance

See `examples/shared/APPROACH_COMPARISON.md` for detailed comparison.

## Technical Documentation

Key docs in `docs/`:
- `transpiration_downregulation_coupling.md` - How water stress affects carbon-water coupling
- `evaporation_computation.md` - Evaporation physics in coupling
- `gross_water_source.md` - Water source term handling
- `timing.md` - Performance profiling notes

## Troubleshooting

**"Make ATS subcycle for proper ELM use"**
- ATS timestep too large for ELM coupling
- Solution: Use subcycling MPC type (see `examples/shared/QUICKSTART.md`)

**Extreme negative pressures (< -1e10 Pa)**
- Richards solver diverging, likely needs smaller timesteps
- Enable subcycling and reduce `subcycling target timestep [s]`

**"No machine <name> found"**
- CIME can't find machine configuration
- Copy templates from `cime_files/` to `~/.cime/`
- Ensure `MACHINE_NAME` matches config file

**NC_FillValue errors**
- E3SM submodule out of date
- Check `$ELM_ATS_SRC_DIR` points to correct commit

**ATS requests evaluator before state initialized**
- See `DEBUG.md` for current debugging approach
- Check ATS XML for correct initialization order

if (COMP_NAME STREQUAL gptl)
  string(APPEND CPPDEFS " -DHAVE_VPRINTF -DHAVE_GETTIMEOFDAY -DHAVE_BACKTRACE")
endif()
set(APPEND FFLAGS " -fallow-argument-mismatch -fallow-invalid-boz")
if (NOT DEBUG)
  string(APPEND FFLAGS " -fno-unsafe-math-optimizations")
endif()
if (DEBUG)
  string(APPEND FFLAGS " -g -fbacktrace -fbounds-check -ffpe-trap=invalid,zero,overflow")
endif()
string(APPEND CXX_LIBS " -lstdc++")
string(APPEND SLIBS " -L$ENV{HDF5_HOME}/lib -lhdf5_fortran -lhdf5 -lhdf5_hl -lhdf5hl_fortran")
string(APPEND SLIBS " -L$ENV{NETCDF_PATH}/lib/ -lnetcdff -lnetcdf -lcurl -lblas -llapack")
set(HDF5_PATH "$ENV{HDF5_HOME}")
set(NETCDF_PATH "$ENV{NETCDF_PATH}")
set(AMANZI_TPLS_DIR "$ENV{AMANZI_TPLS_DIR}")
set(ATS_DIR "$ENV{ATS_DIR}")
if (COMP_CLASS STREQUAL lnd)
  if (NOT ${AMANZI_TPLS_DIR} STREQUAL "")
    string(APPEND FFLAGS " -I${AMANZI_TPLS_DIR}/trilinos-15-1-6af5f44/include")
    string(APPEND FFLAGS " -I${AMANZI_TPLS_DIR}/SEACAS/include ")
    string(APPEND FFLAGS " -I${AMANZI_TPLS_DIR}/petsc-3.20/include -I${AMANZI_TPLS_DIR}/pflotran/src ")
    if (NOT ${ATS_DIR} STREQUAL "")
      string(APPEND CPPDEFS " -DUSE_ATS_LIB ")
      string(APPEND FFLAGS " -I${ATS_DIR}/include ")
    endif()
  endif()
endif()
if (COMP_CLASS STREQUAL cpl)
  string(APPEND LDFLAGS " -lstdc++")
  if (NOT ${AMANZI_TPLS_DIR} STREQUAL "")
    string(APPEND LDFLAGS " -L${AMANZI_TPLS_DIR}/lib")
    string(APPEND LDFLAGS " -L${AMANZI_TPLS_DIR}/trilinos-15-1-6af5f44/lib")
    string(APPEND LDFLAGS " -L${AMANZI_TPLS_DIR}/SEACAS/lib ")
    string(APPEND LDFLAGS " -L${AMANZI_TPLS_DIR}/petsc-3.20/lib -L${AMANZI_TPLS_DIR}/pflotran/src ")
    if (NOT ${ATS_DIR} STREQUAL "")
      string(APPEND LDFLAGS " -L${ATS_DIR}/lib -lerror_handling -latk -lfunctions -lgeometry -lgeochemutil -lgeochemsolvers -lgeochembase -lgeochemrxns -lgeochemistry -lmesh -lmesh_audit -lmesh_simple -lmesh_mstk -lmesh_extracted -lmesh_logical -lmesh_factory -ldbg -lwhetstone -ldata_structures -lmesh_functions -loutput -lstate -lsolvers -ltime_integration -loperators -lpks -lchemistry_pk -ltransport -lshallow_water -lats_operators -lats_eos -lats_surf_subsurf -lats_generic_evals -lats_column_integrator -lats_pks -lats_energy_relations -lats_energy -lats_flow_relations -lats_flow -lats_transport -lats_sed_transport -lats_deform -lats_surface_balance -lats_bgc -lats_mpc_relations -lats_mpc -lelm_ats")
    endif()
  endif()
endif()
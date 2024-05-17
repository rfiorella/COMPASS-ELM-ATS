# Progress with compiling and running ELM-ATS:

Steps to reproduce current issue state:
1. git clone --recursive git@github.com:rfiorella/COMPASS-ELM-ATS
2. cd Docker ; ./deploy-ats-elm-docker.sh
3. grab a cup of coffee, or lunch (this step still needs some optimization)
4. docker run -it metsi/ats:rfiorella-elm_api-1.4-amd64
5. rm /home/amanzi_user/E3SM/cime_config/cmake_macros/userdefined.cmake (conflicts with a .cmake file I added for the container)
7. cd /home/amanzi_user/work/output/f19_g16.IGSWELMBGC/
8. 
9. ./case.build
10. Build will fail, you can look at log files and I've tried to track potential issues as github issues - some of the issues include missing ats libraries, some of which may be expected due to `--disable-geochemistry` (list is: -lgeochemistry -lelm_ats -lmesh_audit -lats_sed_transport. there's also an hdf5 library -lhdf5hl_fortran missing but I think this might be optional for E3SM). If you want to try removing these libraries from the /home/amanzi_user/.cime/gnu-docker_ats.cmake file, do so, then:
11. From /home/amanzi_user/work/output/f19_g16.IGSWELMBGC: ./case.setup --reset; ./case.build --clean-all; ./case.build

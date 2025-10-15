# Current issue to debug: ELM-ATS Initialization

Current ELM-ATS implementation seems to request an 
evaluator before state has been initialized.

Steps to reproduce (using container scripts, but probably similar if you installed on macOS or linux directly):
1) There is a kokkos issue in ELM-ATS API that hasn't been merged, so build ATS from rich/elm-ats-kokkos-patch branch.
For me this is (from the Amanzi repo): `./deploy-ats-docker.sh --amanzi_src_dir='..' --ats_branch='rich/elm-ats-kokkos-patch'` from the rich/debug-deploy amanzi branch
2) From this repo, run `./deploy-ats-elm-docker.sh` (note you may have to change the name of the image in FROM to what ever image is the output of #1)
3) Run the container. E.g., from the root directory of this repo: `docker run -it -e E3SM_WORK_DIR=/home/amanzi_user/work -e ELM_ATS_SRC_DIR=/home/amanzi_user/E3SM -e MACHINE_NAME=docker-ats -e COMPILER_NAME=gnu -v $(pwd):/home/amanzi_user/compass -e HOME=/home/amanzi_user metsi/ats:elm_api`
4) For some reason this install requires git credentials - I put fake ones in the container: 
```  
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```
5) If using the container: `cd compass/examples/oakharbor_column`, then `./build_example.sh` <- this will build ELM and link to ATS. If not using the container, 'compass' is just the root directory of this repo. If you're out of the container, you'll likely need to change a lot of paths in build_example.sh as well to work for your machine, and it's possible it won't compile due to missing cmake files for CIME.
6) If in the container: `cd /home/amanzi_user/work/cases/oakharbor_column && ./case.submit` (or change paths to whatever the case directory was set to in the previous step)
7) This will fail quickly, and give a log file that shows the state/evaluator error.

Additional notes:
- The xml file used to drive ATS is `compass/examples/oakharbor_column/oakharbor_column.xml`
- Base porosity is not specified on the input XML because it is meant to be imported from ELM.

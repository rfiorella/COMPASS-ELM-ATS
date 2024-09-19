# Progress with compiling and running ELM-ATS:

Steps to reproduce current issue state:
1. git clone --recursive git@github.com:amanzi/COMPASS-ELM-ATS
2. cd COMPASS-ELM-ATS/Docker ; ./deploy-ats-elm-docker.sh (there are some issues on M-series Macs here!)
3. grab a cup of coffee, or lunch (this step still needs some optimization)
4. docker run -it metsi/ats:elm_api
Assuming the CI job is still failing, to help debug:
5. ./case.setup --reset (RPF to do: what is the path here?)
6. ./case.build

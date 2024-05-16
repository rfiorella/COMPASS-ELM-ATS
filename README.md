# Progress with compiling and running ELM-ATS:

Steps to reproduce current issue state:
1. git clone --recursive git@github.com:rfiorella/COMPASS-ELM-ATS
2. cd Docker ; ./deploy-ats-elm-docker.sh
3. grab a cup of coffee, or lunch (this step still needs some optimization)
4. docker run -it metsi/ats:rfiorella-elm_api-1.4-amd64
5. cd /home/amanzi_user/work/output/f19_g16.IGSWELMBGC/
6. ./case.build
7. Build will fail, you can look at log files and I've tried to track potential issues as github issues

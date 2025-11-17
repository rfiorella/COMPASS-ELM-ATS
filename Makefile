.PHONY: ELM-ATS-debug

ELM-ATS-debug:
	docker run --rm -it -e E3SM_WORK_DIR=/home/amanzi_user/work -e ELM_ATS_SRC_DIR=/home/amanzi_user/compass -e MACHINE_NAME=docker-ats -e COMPILER_NAME=gnu -v ${CURDIR}:/home/amanzi_user/compass -e HOME=/home/amanzi_user -e GITHUB_ACTIONS=FALSE metsi/ats:elm_api

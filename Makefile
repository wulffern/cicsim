



PYTHON ?= python3

dirs =   tests/sim/ngspice/basic

cwd = ${shell pwd}

.PHONY: docs build

docs = tests/sim/ tests/index tests/plot tests/wave tests/results tests/summary tests/srun tests/simcell tests/template tests/portreplace tests/archive

docs:
	${foreach d, ${docs}, cd ${cwd}; cd ${d} && make docs PYTHON=${PYTHON} || exit  ;}

unit_test:
	cd ${cwd} && ${PYTHON} -m unittest discover -s tests/unittests/ -p 'test_*.py' -v

test: unit_test
	${foreach d, ${dirs}, cd ${cwd}; cd ${d} && make test PYTHON=${PYTHON} || exit  ;}

clean:
	${foreach d, ${dirs}, cd ${cwd}; cd ${d} && make clean || exit  ;}

build:
	-rm -rf build
	-rm -rf dist
	${PYTHON} -m build

test_upload:
	${PYTHON} -m twine upload -u __token__ --repository testpypi dist/*

upload:
	${PYTHON} -m twine upload -u __token__ --repository pypi dist/*

JEKYLL_VERSION=3.8
SITE=${shell pwd}/docs
jstart:
	docker run --rm --name cicsim_docs --volume="${SITE}:/srv/jekyll" -p 3002:4000 -it jekyll/jekyll:${JEKYLL_VERSION} jekyll serve --watch --drafts

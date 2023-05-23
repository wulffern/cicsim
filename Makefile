

dirs =  tests/ip tests/sim/ngspice/basic

cwd = ${shell pwd}

test:

	${foreach d, ${dirs}, cd ${cwd}; cd ${d} && make test ;}

build:
	python3 -m build

test_upload:
	python3 -m twine upload -u wulffern --repository testpypi dist/*

upload:
	python3 -m twine upload -u wulffern --repository pypi dist/*

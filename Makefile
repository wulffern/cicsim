

dirs =   tests/sim/ngspice/basic

cwd = ${shell pwd}

test:
	${foreach d, ${dirs}, cd ${cwd}; cd ${d} && make test || exit  ;}

clean:
	${foreach d, ${dirs}, cd ${cwd}; cd ${d} && make clean || exit  ;}

build:
	python3 -m build

test_upload:
	python3 -m twine upload -u __token__ --repository testpypi dist/*

upload:
	python3 -m twine upload -u __token__ --repository pypi dist/*

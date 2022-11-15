

dirs =  tests/ip tests/sim/ngspice/basic

cwd = ${shell pwd}

test:

	${foreach d, ${dirs}, cd ${cwd}; cd ${d} && make test ;}

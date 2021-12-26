

dirs = tests/sim/BFX1_CV tests/ip

cwd = ${shell pwd}

test:

	${foreach d, ${dirs}, cd ${cwd}; cd ${d} && make test ;}

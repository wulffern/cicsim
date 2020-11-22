
TB=tran
#VIEW=Sch
VIEW=Mdl


OPT=


netlist:
	cicsim netlist --top

typical:
	cicsim run ${TB} ${OPT} ${VIEW} Gt Mtt Rt Ct Tt Vt Dt Bt

slow:
	cicsim run ${TB} ${OPT} ${VIEW} Gt Mss Rh Ch Bf Df "Th,Tl" Vl

fast:
	cicsim run ${TB} ${OPT} ${VIEW} Gt Mff Rl Cl Bs Ds "Th,Tl" Vh

tfs:
	${MAKE} typical slow fast OPT="${OPT}" VIEW="${VIEW}" TB="${TB}"

results:
	python3 results.py  > README.md && cat README.md

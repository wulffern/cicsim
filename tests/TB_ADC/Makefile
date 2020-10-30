
TB=tran
VIEW=Sch
#VIEW=Lay

netlist:
	cicsim netlist --no-top

typical:
	cicsim run ${TB} ${VIEW} Gt Mtt Rt Ct Tt Vt Dt Bl

slow:
	cicsim run ${TB} ${VIEW} Gt Mss Rh Ch Bf Df "Th,Tl" Vl

fast:
	cicsim run ${TB} ${VIEW} Gt Mff Rl Cl Bs Ds "Th,Tl" Vh

tfs:
	${MAKE} typical slow fast


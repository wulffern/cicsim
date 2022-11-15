TB=tran
VIEW=Sch
#VIEW=Lay

OPT=


test:
	${MAKE} typical OPT="Debug"

typical:
	cicsim run --name typical ${TB} ${OPT} ${VIEW}  Tt Vt

tempvall:
	cicsim run --name tempvall ${TB} ${OPT} ${VIEW} "Tt,Th,Tl" "Vt,Vh,Vl"

mc:
	cicsim run --name mc --count 10 ${TB} ${OPT} ${VIEW} Tt Vt

all: typical tempvall mc

clean:
	-rm -rf output_*
	-rm -rf __pycache__
	-rm *.run
	-rm *.pdf
	-rm *.csv

test: all

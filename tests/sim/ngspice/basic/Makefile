TB=tran
VIEW=Sch
#VIEW=Lay

OPT=


typical:
	cicsim run --name ${VIEW}_typical ${TB} ${OPT} ${VIEW}  Tt Vt

tempvall:
	cicsim run --name ${VIEW}_tempvall ${TB} ${OPT} ${VIEW} "Tt,Th,Tl" "Vt,Vh,Vl"

mc:
	cicsim run --name ${VIEW}_mc --count 10 ${TB} ${OPT} ${VIEW} Tt Vt

all: typical tempvall mc summary

clean:
	-rm -rf output_*
	-rm -rf __pycache__
	-rm *.run
	-rm *.pdf
	-rm *.csv

summary:
	cicsim summary --output "README.md"

test: all

---
layout: page
title:  plot 
math: true
---


* TOC
{:toc }


`plot` is a command to read a raw file from ngspice (or other spice), and show a
plot
or save a plot to a file. 

I made `plot` before I made `wave`, so there is some overlap in features. 

I would recommend `plot` for when you want to plot via a script, or indeed, see
how you could write your own python code around the plot functions


## Command

<!--run_output:
run: cicsim plot --help
-->


## Simple plotting

There is an example raw file in `tests/plot`. Navigate to that directory


<!--run_image:
run: cicsim plot test.raw time "v(vn)" --fname "plot_1.svg" --no-show
output_image: plot_1.svg
-->

## If you don't know the nodes 

If you don't know the node that the raw file contains, then just guess, and plot 
will tell you what the raw contains.

<!--run_output:
run: cicsim plot test.raw time "somenode"  --no-show
-->


## Plot options

It's possible to plot multiple nodes in the same figure 

<!--run_image:
run: cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_2.svg" --no-show
output_image: plot_2.svg
-->


### same

Or you can also share the plot using the `--ptype`  option `"same"`


<!--run_image:
run: cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_3.svg" --ptype "same" --no-show
output_image: plot_3.svg
-->



The plot options are a comma separated list of options.


### logy

<!--run_image:
run: cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_4.svg" --ptype "same,logy" --no-show
output_image: plot_4.svg
-->

### ln2

<!--run_image:
run: cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_5.svg" --ptype "same,ln2" --no-show
output_image: plot_5.svg
-->

### logx

<!--run_image:
run: cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_6.svg" --ptype "same,logx" --no-show
output_image: plot_6.svg
-->

### db20

<!--run_image:
run: cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_7.svg" --ptype "same,db20" --no-show
output_image: plot_7.svg
-->

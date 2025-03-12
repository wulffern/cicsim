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

```bash
cicsim plot --help
```

```bash
Usage: cicsim plot [OPTIONS] FILENAME XNAME YNAME

  Plot from rawfile

  Example:

      Plot vp and vn versus time.

      $ cicsim plot test.raw time "v(vp),v(vn)"

      Plot vp and vn in the same plot

      $ cicsim plot test.raw time "v(vp),v(vn)" --ptype "same"



Options:
  --ptype TEXT        Plot options
  --show / --no-show  Show plot or not
  --fname TEXT        Plot filename
  --help              Show this message and exit.

```



## Simple plotting

There is an example raw file in `tests/plot`. Navigate to that directory


```bash
cicsim plot test.raw time "v(vn)" --fname "plot_1.svg" --no-show
```

![](/cicsim/assets/plot_1.svg)
## If you don't know the nodes 

If you don't know the node that the raw file contains, then just guess, and plot 
will tell you what the raw contains.

```bash
cicsim plot test.raw time "somenode"  --no-show
```

```bash
2025-03-12 09:17:41.497 Python[90386:386793816] ApplePersistenceIgnoreState: Existing state will not be touched. New state will be written to /var/folders/rk/945ntwx556l83qk8p1t64zdw0000gn/T/org.python.python.savedState
[31mError: Could not find name time in time,i(vibp),v(c1a_1v8),v(c1b_1v8),v(c2a_1v8),v(c2b_1v8),v(cmp_o),v(coarse),v(d_coarse),v(d_fine),v(d_state),v(idac_o0),v(idac_o1),v(idac_o2),v(idac_o3),v(res_n_1v8),v(state0),v(valid),v(vn),v(vp),v(xdut.idac_o<0>),v(xdut.x1.bp0),v(xdut.x1.bp1),v(xdut.x1.bp2),v(xdut.x1.bp3),v(xdut.x1.bp4),v(xdut.x1.bp5),v(xdut.x1.bp6),v(xdut.x1.bp7),v(xdut.x1.pwr_n),v(xdut.x1.vd),v(xdut.x1.vgp),v(xdut.x1.vs)[0m

```



## Plot options

It's possible to plot multiple nodes in the same figure 

```bash
cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_2.svg" --no-show
```

![](/cicsim/assets/plot_2.svg)

### same

Or you can also share the plot using the `--ptype`  option `"same"`


```bash
cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_3.svg" --ptype "same" --no-show
```

![](/cicsim/assets/plot_3.svg)


The plot options are a comma separated list of options.


### logy

```bash
cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_4.svg" --ptype "same,logy" --no-show
```

![](/cicsim/assets/plot_4.svg)
### ln2

```bash
cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_5.svg" --ptype "same,ln2" --no-show
```

![](/cicsim/assets/plot_5.svg)
### logx

```bash
cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_6.svg" --ptype "same,logx" --no-show
```

![](/cicsim/assets/plot_6.svg)
### db20

```bash
cicsim plot test.raw time "v(vn),v(vp)" --fname "plot_7.svg" --ptype "same,db20" --no-show
```

![](/cicsim/assets/plot_7.svg)
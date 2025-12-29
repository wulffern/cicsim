---
layout: page
title:  run 
math: true
---

* TOC
{:toc }

## Command
```bash
cicsim --no-color run --help
```

```bash
Usage: cicsim run [OPTIONS] TESTBENCH [CORNER]...

  Run a ngspice simulation of TESTBENCH

Options:
  --run / --no-run        Run simulator
  --count INTEGER         Run each corner count times, useful for Monte-Carlo
  --name TEXT             Control name of run file
  --ignore / --no-ignore  Ignore error checks
  --sha / --no-sha        Check SHA of input files
  --replace TEXT          YAML file with replacements for netlist
  --help                  Show this message and exit.

```



## Motivation

An analog simulation requires a testbench. A SPICE file where the conditions
(voltages, currents, temperatures, process ), device under test (DUT), stimuli
and measurements are defined.

Most simulators, ngspice included, take a single SPICE file as input, and the
simulators
expects that everything is defined within that spice file.

Take the spice netlist below as an example. 

ngspice/basic/tran_SchTtVt.spi:
```spice
*cicsimgen tran

.param SEED=0

.option TEMP=27

.param vdda = 1.8

```


This is just an excerpt, but notice that both the `vdda`, the supply voltage,
and the temperature is defined in the spice file. 

When we design analog circuits, we must test over all temperatures (-40,25,125),
all supply voltages (1.7,1.8,1.9), process corners (slow, typical, fast),
statistical variation (local variation, global variation) and maybe much more. 

The number of corners (one permuatation of the conditions above) we have to
check can easily be in the ten's to hundreds of corners.

Now imagine, that you have to change each of the 100 spice files, just to add
the corner. 

Hopefully, that's enough to convince you that you should *never* manually write
the corners into the SPICE file. You need automation!

## Principles 

`cicsim` takes a testbench template, and a set of corners as input. 

The script proceeds to generate all the necessary SPICE files, and runs the
corners 

An example can be seen in the
[tests/sim/](https://github.com/wulffern/cicsim/tree/main/tests/sim) directory.

For example, to run typical corner, over temperature/voltage and monte-carlo
local variation I can do.


```bash
cd ngspice/basic ; make -n all
```

```bash
cicsim run --name Sch_typical tran  Sch  Tt Vt
cicsim run --name Sch_tempvall tran  Sch "Tt,Th,Tl" "Vt,Vh,Vl"
cicsim run --name Sch_mc --count 10 tran  Sch Tt Vt
cicsim summary --output "README.md"

```


And I get a summary of the simulation results.







|**Name**|**Parameter**|**Description**| |**Min**|**Typ**|**Max**| Unit|
|:---|:---|:---|---:|:---:|:---:|:---:| ---:|
|**Divider voltage**|**vx** || **Spec**  | **0.80** | **0.90** | **1.00** | **V** |
| | | |Sch_typical| | 0.91 |  | |
| | | |Sch_tempvall|0.82 | 0.91 | 1.00 | |
| | | |Sch_3std|0.87 | 0.91 | 0.95 | |




## Why is this cool?

If you're new to analog simulation, then you might not understand what just
happened.

You might even say "I want a testbench in Xschem, I can just put the corners as
a symbol", or "This seems way too complicated, I just want something easy". 

If you're new, then you might not listen to advice, but here is some advice
anyway. 

You may have to re-run all simulations in 5 years when your customer
complains, and your circuit does not work. You will have forgotten how to run the testbenches, or indeed,
what corners you simulated, so you better write it down. If you make sure that all the testbenches, and simulations, can be run with
one command, for example `make all`, then your life will be easier.

It's always worth the effort to go the extra mile to setup automatic simulations. 

_Warning_: I wrote `cicsim`  for me, no-one else. That means, it might not be for you. 

I've forced approx 100 students to use `cicsim`, and in the end, I do think they
understood why it's necessary. You may also understand one day. 
   
   
## The `cicsim.yaml` and corners

The "corners" are the  `Sch "Tt,Th,Tl" "Vt,Vh,Vl"` part of the command above.
But somehow `cicsim` must know what those corners mean. 

All corner information is in the `cicsim.yaml` file. `cicsim` will search the
current directory, and the parent directory for a `cicsim.yaml` file. 

The directory structure I use often looks like
[sun\_pll\_sky130nm/sim](https://github.com/wulffern/sun_pll_sky130nm/tree/main/sim)

```python
ROSC          # ring oscillator simulation
- cicsim.yaml # local ring oscillator setup 
SUN_PLL_BUF   # buffer simulation
- cicsim.yaml # local buffer setup 
SUN_PLL       # top level simulation 
- cicsim.yaml # local top  setup
cicsim.yaml   # where all the magic happens 
```

The local setup files usually don't contain much info. Something like this is
sufficient 

```yaml
corner:
  Lay: ''
  Sch: ''
ngspice:
  cell: SUN_PLL_BUF
```

The corners "Lay" (Layout) and "Sch" (Schematic) are defined locally. For analog
simulations we also need to re-run simulations after we've done the layout, and
extracted parasitics. That's why there are two "corners", or "views" (Sch,Lay)

In the "magic"
[`cicsim.yaml`](https://github.com/wulffern/tech_sky130A/blob/main/cicsim/cicsim.yaml)
all the corners are defined. 

An excerpt from the file above is shown below.

```yaml
corner:
  Tt: |
    .lib "../../../tech/ngspice/temperature.spi" Tt
  Tl: |
    .lib "../../../tech/ngspice/temperature.spi" Tl
  Th: |
    .lib "../../../tech/ngspice/temperature.spi" Th
  Vt: |
    .lib "../../../tech/ngspice/supply.spi" Vt
  Vl: |
    .lib "../../../tech/ngspice/supply.spi" Vl
  Vh: |
    .lib "../../../tech/ngspice/supply.spi" Vh
  Att: |
    .lib  "$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice" tt
  Asf: |
    .lib  "$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice" sf
```


**cicsim will insert the text defined in cicsim.yaml for a corner into the
generated spice file**

For example, the command `cicsim run tran Sch Att Th Vh ` would read `tran.spi`
and insert the
following into the generated spice file `output_tran\tran_SchAttThVh.spi`

```

.lib "../../../tech/ngspice/temperature.spi" Th

.lib "../../../tech/ngspice/supply.spi" Vh

.lib  "$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice" tt

```

## The testbench (tran.spi)

An example testbench can be seen below (from
[ngspice/basic/tran.spi](https://github.com/wulffern/cicsim/blob/main/tests/sim/ngspice/basic/tran.spi))

You can write anything in the SPICE file that ngspice understands. `cicsim` does
have some advanced features (like the `#ifdef`), however, you don't need to use them if you don't
want to. 

ngspice/basic/tran.spi:
```SPICE
*Demo of cicsim
*-----------------------------------------------------------------
* OPTIONS
*-----------------------------------------------------------------
.option TNOM=27 GMIN=1e-15 reltol=1e-3
*-----------------------------------------------------------------
* PARAMETERS
*-----------------------------------------------------------------
.param TRF = 10p
.param AVDD = {vdda}
*-----------------------------------------------------------------
* FORCE
*-----------------------------------------------------------------
VSS  VSS  0     dc 0
VDD  VDD_1V8  VSS  dc {AVDD}
*-----------------------------------------------------------------
* DUT
*-----------------------------------------------------------------
R1 VDD_1V8 VX 1k m=agauss(1,0.1,3)
R2 VX VSS 1k m=agauss(1,0.1,3)
*----------------------------------------------------------------
* PROBE
*----------------------------------------------------------------
#ifdef Debug
.save all
#else
.save i(R1) v(VX)
#endif
*----------------------------------------------------------------
* NGSPICE control
*----------------------------------------------------------------
.control
set num_threads=8
set color0=white
set color1=black
unset askquit
optran 0 0 0 100p 2n 0
tran 10p 10n 1p
write
quit
.endc
.end

```


## The output file 

`cicsim` will always make a `output_<testbench>` directory, and write the corner 
files there. The simulation also runs from the output directory. 

As such, if you have any reference to other spice files, for example the device
under test, then you need to remember the extra "../"

For example, if you have the files 

``` 
tran.spi
xdut.spi 
```

then, inside `tran.spi` you would reference the `xdut.spi` with 

```
.include "../xdut.spi"
```

## The simulation run 

`cicsim` will tell you what it does. For example: 

```
cicsim run --name Sch_typical tran  Sch  Tt Vt
```

First you will see the simulation running, we can also see the exact command
that `cicsim` uses to run the output spice file.  

```
Running tran_SchTtVt
cd output_tran; ngspice -b  tran_SchTtVt.spi -r tran_SchTtVt.raw 2>&1 |tee tran_SchTtVt.log
...
Corner simulation time : 0:00:00.077743
```

After the simulation has completed, `cicsim` will search for a
`<testbench>.meas` file. A "meas" file is really just a SPICE file, but it
contains only measurements. 



Below is the output from the measurement section of the `cicsim` run 

```
cd output_tran; ngspice -b tran_SchTtVt.meas  2>&1 | tee tran_SchTtVt.logm
...
vx                  =  8.971411e-01 from=  0.000000e+00 to=  1.000000e-08
...
Writing output_tran/tran_SchTtVt.yaml
Total simulation time : 0:00:00.131207
```
The measurements are stored into a YAML file for that particular corner 

After all simualtions have completed, then `cicsim` will search for a
`<testbench.py>` file. Here you could have a additional python post processing
for the YAML file, or automatically generate plots, or whatever you want. 

```
Running tran.py with output_tran/tran_SchTtVt
Output contains following parameters ['vx']
``` 

If there is a `<testbench.yaml>` file, then `cicsim` will generate a summary of
the simulation results. In the YAML file the name, min, typ, max, scale, digits,
units and others are defined.

```
|      vx | name         | time                     | type   |
|---------|--------------|--------------------------|--------|
| 0.89714 | tran_SchTtVt | Fri Jul 26 22:47:52 2024 | Sch    |
Writing CSV results/tran_Sch_typical.csv
```

## The measurement file 

It's a good idea to separate long simulations and the measurements you do on the
waveforms. It's no fun to rerun hours of simualtion just because you got the
measurement wrong. 

During debugging on of the measurements it's also an advantage to be able to not
re-run the simulation. The option "--no-run" does just that 

```bash
cicsim run --name Sch_typical tran  Sch  Tt Vt --no-run
```

The measurement file is shown below. The "{cicname}" will be replaced by what 
the corner is called.

Any measurement between "MEAS\_START" and "MEAS\_END" will be post processed by `cicsim`

ngspice/basic/tran.meas:
```
* Measure
.control

load {cicname}.raw

echo "MEAS_START"

meas tran vx avg v(vx)


echo "MEAS_END"
.endc

```


## The python file 

An example of a python script is shown below

ngspice/basic/tran.py:
```python
import sys
import os
import cicsim
import yaml

@cicsim.SimCalcYaml
def main(fname,df):
    df.to_csv(fname + ".csv")
    print("Output contains following parameters " + str(list(df.columns)))


```


The attribute `@cicsim.SimCalcYaml` will read in the corner output YAML file and
load it as a dataframe. The `fname` option is the name of the corner
(`tran_SchThVh`). 

The python script can do whatever you want.

> <span style='color:red'> **Warning**</span>
> cicsim will happily execute all python code. So be careful running simulations
> from others.



## Advanced features 

### ifdef/else

In the testbench you can use the #ifdef/else syntax 

```
#ifdef Debug
.save all
#else
.save i(R1) v(VX)
#endif
```

For example, 

```
cicsim run --name Sch_typical tran Debug Sch  Tt Vt
```

would include the 

```
.save all
```

into the output SPICE file, while 

```
cicsim run --name Sch_typical tran  Sch  Tt Vt
```

would include

```
.save i(R1) v(VX)
```

### --replace 

The replace option takes a YAML file with keywords to replace in the testbench.

ngspice does not support parameters in the `.control` section, and sometimes
it's useful to have parameters that span multiple testbenches. 

Take the "replace.yaml" below 

```YAML
clock_period: 250e-9
nbpt: 6*(9+9+2)
temp_sweep: -25 0 25 50 75 100
```

And running 

```
cicsim  run  --replace replace.yaml --name Sch_typical tran Sch Gt Kss Tt Vl
```

In the testbench I have the line 

```
tran [{clock_period}/50] [{clock_period}*(16+{nbpt})] [{clock_period}*16]
```

The first thing `cicsim` will do is to replace the keywords, resulting in 

```
tran [250-9/50] [250e-9*(16+6*(9+9+2))] [250e-9*16]
```

As of yet, the above statement is not a valid ngspice line. `cicism` also has
the ability to parse expressions 


### [expression]

In the testbench `cicsim` will attempt to evaulate any expression matching the 
regular expression pattern "\s+\[([^\]]+)\]" (translated to human speak:
anything that starts with a space, and is inside brakets [ ], for example "
[2*2]")

There is a conflict with the pattern used by `d_cosim`, but so far it seems to
be ignored ("adut [ din ] [ dout ] null dut").

The previous line 

```
tran [250-9/50] [250e-9*(16+6*(9+9+2))] [250e-9*16]
```

would in the output spice file be replaced by 

```
tran 5e-09 3.4e-05 4e-06
```

### Don't run simulations if nothing has changed 

A feature that is by default turned off is the hashing algorithm for all
includes. 

If you add  the below to your `cicsim.yaml` the hashing will be enabled. 
```
options:
  sha: True
```

As cicsim reads the testbench it will search for ".include" and ".lib"
statements and find all referenced files. For each of the file it 
will generate a SHA1 hash, which will be saved to a ".sha" file in the "output_"
directory.

The sha file may look like this
```
../../../tech/ngspice/supply.spi: 979119a85f3fabb437b7966ff0840ad719b7d206cd755226625b69abc60da697
../../../tech/ngspice/temperature.spi: ae70f497d3f601cb938b76585b4635003d9221716e3ea52c012fe76e609a052b
../../../work/lpe/SUNSAR_CDAC8_CV_lpe.spi: 9d54993102e1964767a62b1639da4fb0f507a7de2af961b788f1e546c591ec8a
../../../work/xsch/JNWG00_CORE.spice: 9461bb25fb0f2fd3fefcedc1376fdbba669f14ea6779e92c57de6db2efceb28b
../xdut.spi: be90e69e17ab34394c447c100c8a15bb2611138c390a57175b97e1ff565c5b3c
/opt/pdk/share/pdk/sky130A/libs.ref/sky130_fd_pr/spice/sky130_fd_pr__nfet_01v8__ff.pm3.spice: 7f5d15ae3bdc466cab33f6c85bedb7293e20b1e6932c924a0a288aa5aef00290
/opt/pdk/share/pdk/sky130A/libs.ref/sky130_fd_pr/spice/sky130_fd_pr__nfet_01v8__mismatch.corner.spice: 24a3b29d7d7f26f99098811c31eb5497950a3aed520ab83768a96f35467fe818
/opt/pdk/share/pdk/sky130A/libs.ref/sky130_fd_pr/spice/sky130_fd_pr__pfet_01v8__ff.corner.spice: 30ba71bde4024ff291a68352930bf2fc3e07f627efb090e1575b9dbd7b6e75da
/opt/pdk/share/pdk/sky130A/libs.ref/sky130_fd_pr/spice/sky130_fd_pr__pfet_01v8__mismatch.corner.spice: f4d560668712678ea60641de923fce7691e64acda951949f840986837c31741a
/opt/pdk/share/pdk/sky130A/libs.tech/ngspice/all.spice: ada86dba53017af314dfa04dac253c8424e0941158cf476a7ca191c55aea3bbb
/opt/pdk/share/pdk/sky130A/libs.tech/ngspice/corners/ff/nonfet.spice: d03e3604898888b64c71a6ddba5f03dd8a05b298ac6a10a5dc2ae1c01ab73a74
/opt/pdk/share/pdk/sky130A/libs.tech/ngspice/corners/ff/specialized_cells.spice: 3f6580d1d5c7997a747964fee6e145dddfc2aaa66d18e0707fe76972a436f127
/opt/pdk/share/pdk/sky130A/libs.tech/ngspice/r+c/res_typical__cap_typical.spice: 7c29723076a22fe5b080d245adb97451de5ad0812f0344f6bfe31c9697b71f0d
/opt/pdk/share/pdk/sky130A/libs.tech/ngspice/r+c/res_typical__cap_typical__lin.spice: 4deedaa4be27f2e1f083567a945cbaed02027e018fcd09431e57a02c08a117b1
stable_SchGtKffTtVh.meas: ff0710ed4624e7c3d15fb37cfef10afd60e5e530c40db85889fd066f177dd88f
stable_SchGtKffTtVh.spi: ca62315665f25645032688195273ac4c454d4b99274994e3bab23d8ab2412832
```

Should the SHA file already exist for the corner, then `cicsim` will read all
the SHA's and check if any of the input files have changed (compare new versus
old hash). If none of the SHAs have changed, then `cicsim` will skip simulating
again. 

It does take a bit of time to calculate the SHA's, but it's much faster than
running the simulation. 

I find it a useful feature to check if I've modified anything. Also, I don't
need to worry about re-running simulations. If nothing has changed, then the
simulation won't run.

## Archive

Use the `cicsim  archive` command if you want to save a simulation set for a later date, for example if you intend
to re-run your typical simulation, but you really want to save the old
simulation do

```bash
cd ngspice/basic ; cicsim --no-color archive "My Sim" tran_Sch_typical.run tran_Sch_mc.run
```

```bash
Info: cp output_tran/tran_SchTtVt* archive/2025-12-29_19-31_My_Sim[0m
Info: writing archive/2025-12-29_19-31_My_Sim_tran_Sch_typical.run[0m
Info: cp output_tran/tran_SchTtVt* archive/2025-12-29_19-31_My_Sim[0m
Info: cp output_tran/tran_SchTtVt_1* archive/2025-12-29_19-31_My_Sim[0m
Info: cp output_tran/tran_SchTtVt_2* archive/2025-12-29_19-31_My_Sim[0m
Info: cp output_tran/tran_SchTtVt_3* archive/2025-12-29_19-31_My_Sim[0m
Info: cp output_tran/tran_SchTtVt_4* archive/2025-12-29_19-31_My_Sim[0m
Info: cp output_tran/tran_SchTtVt_5* archive/2025-12-29_19-31_My_Sim[0m
Info: cp output_tran/tran_SchTtVt_6* archive/2025-12-29_19-31_My_Sim[0m
Info: cp output_tran/tran_SchTtVt_7* archive/2025-12-29_19-31_My_Sim[0m
Info: cp output_tran/tran_SchTtVt_8* archive/2025-12-29_19-31_My_Sim[0m
Info: cp output_tran/tran_SchTtVt_9* archive/2025-12-29_19-31_My_Sim[0m
Info: writing archive/2025-12-29_19-31_My_Sim_tran_Sch_mc.run[0m

```










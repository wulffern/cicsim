import sys
import os
import cicsim
import yaml

@cicsim.SimCalcYaml
def main(fname,df):
    df.to_csv(fname + ".csv")
    print("Output contains following parameters " + str(list(df.columns)))

if __name__ == "__main__":
    fname = sys.argv[1]
    main(fname)

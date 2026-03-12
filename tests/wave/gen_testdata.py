#!/usr/bin/env python3
"""Generate test CSV data for wave documentation examples."""

import numpy as np
import pandas as pd

t = np.linspace(0, 2e-6, 2000)

vp = 0.9 + 0.4 * np.sin(2 * np.pi * 2e6 * t)
vn = 0.9 - 0.4 * np.sin(2 * np.pi * 2e6 * t)
vout = np.where(vp > vn, 1.8, 0.0)
ibias = 50e-6 + 5e-6 * np.sin(2 * np.pi * 2e6 * t)

df = pd.DataFrame({
    "time": t,
    "v(vp)": vp,
    "v(vn)": vn,
    "v(out)": vout,
    "i(ibias)": ibias,
})
df.to_csv("test.csv", index=False)
print("Wrote test.csv")

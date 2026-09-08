#!/usr/bin/env python3
"""
layer_division_twin_1218.py -- synthetic twin for layer_division_1218.py.
A fake crossing table with 40 % of labels dropped at random on each plane.
    python layer_division_twin_1218.py equal    -> COMPATIBLE (error 0.02 pitch)
    python layer_division_twin_1218.py uneven   -> N WRONG (judge sees more sheets than layers)
"""
import numpy as np, sys
mode = sys.argv[1]   # equal | uneven
rng = np.random.default_rng(0)
zs = list(range(1000, 1000+32*20, 32)); zpos = {z:i for i,z in enumerate(zs)}
rows = []
for z in zs:
    for i in range(60):
        # true sheets: equal pitch 11.6 (+ small noise) or uneven pitch
        if mode == "equal":
            steps = 11.6 + rng.normal(0, 0.4, 40)
        else:
            steps = 11.6 * rng.uniform(0.45, 1.55, 40)
        r = 100 + np.cumsum(steps)
        # label dropout 40 %, independent per plane
        keep = rng.random(40) > 0.4
        for k, rk in enumerate(r[keep]):
            rows.append(dict(z=str(z), theta_deg=str(i*6.0), k=str(k), r_l1_vox=str(rk), r_um="0"))
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'layer_division_1218.py')).read())

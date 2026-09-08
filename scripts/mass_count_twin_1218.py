#!/usr/bin/env python3
"""
mass_count_twin_1218.py -- synthetic twin for mass_count_1218.py.
A fake table and a fake level-1 CT with sheets of constant mass, continuous in z,
hidden sheets seen by ~1/3 of planes.
    python mass_count_twin_1218.py pressed   -> MASS COUNTS (pitch 0.6x, same mass: pitch count fails, mass passes)
    python mass_count_twin_1218.py uniform   -> NO DIFFERENCE (both pass)
The twin also exposed that "exact agreement with the judge" rewards under-counting,
because the judge misses hidden sheets; the verdict rests on E1 and E2 only.
"""
import numpy as np, sys
mode = sys.argv[1]   # pressed | uniform
rng = np.random.default_rng(0)
zs = list(range(1000, 1000+32*16, 32)); zpos = {z:i for i,z in enumerate(zs)}
ox, oy = 700.0, 700.0
P = 11.6
# true sheets per (ray, plane): a spiral-free radial list; packs of 2-5 sheets pressed (pitch x0.6) or not
truth = {}; rows = []
# sheet structure per ray, CONTINUOUS in z (same sheets on every plane, small wobble)
base = {}
for i in range(60):
    r = [100.0]; lab = [True]
    while r[-1] < 560:
        if rng.random() < 0.25:
            npk = rng.integers(2, 6); pitch = P * (0.6 if mode == "pressed" else 1.0)
            for j in range(npk):
                r.append(r[-1] + pitch + rng.normal(0, .2)); lab.append(j == npk - 1)
        else:
            r.append(r[-1] + P + rng.normal(0, .3)); lab.append(True)
    base[i] = (np.array(r), np.array(lab))
for z in zs:
    for i in range(60):
        r, lab = base[i]; rz = r + rng.normal(0, .3, len(r))
        truth[(i, z)] = list(zip(rz, lab))
        k = 0
        for x, l in truth[(i, z)]:
            if l or rng.random() < 0.35:            # hidden sheets seen by ~1/3 of planes
                rows.append(dict(z=str(z), theta_deg=str(i*6.0), k=str(k), r_l1_vox=str(x), r_um="0")); k += 1
origins_ct = {z:(ox, oy) for z in zs}
TH = 4.0   # sheet thickness in level-1 voxels, same mass everywhere
class L1:
    def __getitem__(s, key):
        z, ysl, xsl = key
        yy = np.arange(ysl.start, ysl.stop)[:, None].astype(float); xx = np.arange(xsl.start, xsl.stop)[None, :].astype(float)
        rr = np.hypot(xx - ox, yy - oy); ang = np.degrees(np.arctan2(yy - oy, xx - ox)) % 360
        i = int(round(ang.mean() / 6)) % 60                 # box is small: one ray
        img = np.full(rr.shape, 20.0)
        for x, _ in truth[(i, int(z))]:
            img[np.abs(rr - x) < TH / 2] = 120
        return (img + rng.normal(0, 5, img.shape)).astype(np.float32)
ct_root = {"1": L1()}
import os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mass_count_1218.py')).read().replace("N_PACKS = 3000", "N_PACKS = 600")
exec(src)

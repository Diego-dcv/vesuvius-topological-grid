#!/usr/bin/env python3
"""
fold_check_twin_1218.py -- synthetic twin for fold_check_1218.py.
40 straight windings per ray plus 6 planted wave folds (a crossing pair that
opens parabolically below an apex plane and is absent above), 30 % of labels
missing. Scores the detector against the planted truth.
RESULT ON RECORD (8 Sep, third version): planted fold crossings flagged 38-60 %
depending on the criterion, true windings flagged 7-11 %. Insufficient: with
split labels merged (< 7 vox), a fold pair near its apex is already one
crossing and the open part of the wave looks like a missing label.
"""
import numpy as np, sys
rng = np.random.default_rng(5)
zs = list(range(1000, 1000+32*30, 32)); zpos = {z:i for i,z in enumerate(zs)}
P = 11.6; rows = []; truth_fold = {}   # (z,i) -> set of fold radii (rounded)
for i in range(60):
    base = 100 + P*np.arange(40) + rng.normal(0, .3, 40)     # 40 straight windings
    # plant 6 wave folds per ray: a pair that opens parabolically below an apex plane and is absent above
    folds = []
    for _ in range(6):
        k = rng.integers(3, 37); apex = rng.integers(6, 24); half = rng.integers(4, 9)   # visible on planes apex-half..apex
        folds.append((base[k] + P*0.5, apex, half))
    for iz, z in enumerate(zs):
        r = list(base + rng.normal(0, .3, 40)); f_here = []
        for (rc, apex, half) in folds:
            if apex - half <= iz <= apex:
                w = 0.45*P * np.sqrt((apex - iz + 0.5) / half)     # half-separation, closes at the apex
                r += [rc - w, rc + w]; f_here += [rc - w, rc + w]
        r = np.sort(r); truth_fold[(z, i)] = f_here
        keep = rng.random(len(r)) > 0.3            # 30 % of labels missing
        k = 0
        for x, kp in zip(r, keep):
            if kp: rows.append(dict(z=str(z), theta_deg=str(i*6.0), k=str(k), r_l1_vox=str(x), r_um="0")); k += 1
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fold_check_1218.py')).read())
# score against the planted truth
hit = tot = fp = wt = 0
for (i, iz), (rr, isp, p) in cols.items():
    fl = fold_flag[(i, iz)]; tf = truth_fold[(zs[iz], i)]
    for x, f in zip(rr, fl):
        is_fold = any(abs(x - y) < 2.0 for y in tf)
        if is_fold: tot += 1; hit += f
        else: wt += 1; fp += f
print(f"TWIN: planted fold crossings flagged {hit/tot:.0%} (target >= 80%); true windings flagged {fp/wt:.1%} (target <= 5%)")

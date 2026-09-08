#!/usr/bin/env python3
"""
layer_division_1218.py — FUSED PACKS DIVIDED INTO EQUAL LAYERS: is the division
compatible with the sheets the labels DO know one plane away?

IDEA (Diego, 7 Sep). Where the crossing table shows two labelled sheets in a
row with a gap too wide for one sheet, the gap is a pressed pack hiding n-1
sheets. Divide it into n equal layers; each layer is one winding. Then check
whether that assignment is compatible with what is known elsewhere.

JUDGE. The same ray on the neighbouring plane (0.55 mm above or below), where
the labels sometimes DO see one of the hidden sheets. The two sheets bounding
the pack are matched on the neighbouring plane by nearest radius (within half
a local pitch); any labelled crossing strictly inside the matched interval is
a hidden sheet made visible. Its radius is compared with the nearest predicted
layer position.

PRE-REGISTERED EXAM:
  E1 count: the neighbouring plane never shows MORE sheets inside the pack
     than the n-1 layers predicted, in >= 90 % of packs (else the pitch-based
     n is wrong and the division means nothing).
  E2 position: median |error| of the prediction, in units of the local pitch,
     must be < 0.6 x the median error of RANDOM positions inside the same gap
     (bootstrap CI95 of the ratio excluding 0.6). Chance: ratio ~ 1.
  Both pass -> COMPATIBLE. E1 fails -> n is wrong. E2 fails -> equal division
  is no better than chance.
  Also reported: the same judge on the neighbouring RAY (6 deg away), where
  the half-pitch drift is known to bite.
SPLIT LABELS (added 8 Sep). 31 % of consecutive crossings are one label cut in
two (< 7 vox apart). Left as they are, the judge counts a split label as two
sheets and E1 fails by a hair: "more sheets than layers" in 10.5 % of packs
(recorded run, MERGE_SPLIT = False). With crossings < 7 vox merged before the
search (MERGE_SPLIT = True, the default now) it is 2.0 % of 240,661 packs and
E1 passes; E2 is unchanged (35 um). The neighbouring-ray judge, 6 deg away,
gives the same 35 um: the linear mapping between the matched bounding sheets
absorbs the angular drift.
INPUT. The crossing table only (pherc1218_io). No CT. Runs in ~6 min.
OUTPUT. layer_division_1218.npz, layer_division_1218.png
"""
if "rows" not in dir():
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)) if "__file__" in dir() else "scripts")
    from pherc1218_io import load_all
    globals().update(load_all(ct=False))

import numpy as np, matplotlib.pyplot as plt, time
t0 = time.time()
VOX = 0.01728
GAP_MIN = 1.6          # a gap >= GAP_MIN x local pitch is a pack (n >= 2)
MERGE_SPLIT = True     # merge crossings < SPLIT_TOL vox apart (split labels) before the search
SPLIT_TOL = 7.0
rng = np.random.default_rng(7)

kmax = max(int(r["k"]) for r in rows); nzp = len(zs)
Rg = np.full((kmax + 1, 60, nzp), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]), int(round(float(r["theta_deg"]) / 6)) % 60, zpos[int(r["z"])]] = float(r["r_l1_vox"])


def column(i, iz):
    rs = Rg[:, i, iz]; rs = np.sort(rs[np.isfinite(rs)])
    if MERGE_SPLIT and len(rs) > 1:
        out, grp = [], [rs[0]]
        for x in rs[1:]:
            if x - grp[-1] < SPLIT_TOL:
                grp.append(x)
            else:
                out.append(np.mean(grp)); grp = [x]
        out.append(np.mean(grp)); rs = np.array(out)
    return rs


def local_pitch(rs):
    d = np.diff(rs)
    if len(d) < 4:
        return None
    m = np.median(d)
    ok = d[(d > 0.5 * m) & (d < 1.5 * m)]      # "normal" gaps only
    return float(np.median(ok)) if len(ok) >= 3 else None


packs = []      # one record per (pack, judge)
for iz in range(nzp):
    for i in range(60):
        rs = column(i, iz)
        p = local_pitch(rs)
        if p is None:
            continue
        for a in range(len(rs) - 1):
            g = rs[a + 1] - rs[a]
            if g < GAP_MIN * p:
                continue
            n = int(round(g / p))
            if n < 2:
                continue
            pred = rs[a] + g * np.arange(1, n) / n           # n-1 hidden positions
            for judge, (j_i, j_iz) in [("plane", (i, iz - 1)), ("plane", (i, iz + 1)),
                                       ("ray", ((i - 1) % 60, iz)), ("ray", ((i + 1) % 60, iz))]:
                if not (0 <= j_iz < nzp):
                    continue
                qs = column(j_i, j_iz)
                if len(qs) < 4:
                    continue
                # match the two bounding sheets on the judge column
                ia = np.argmin(np.abs(qs - rs[a])); ib = np.argmin(np.abs(qs - rs[a + 1]))
                if abs(qs[ia] - rs[a]) > 0.5 * p or abs(qs[ib] - rs[a + 1]) > 0.5 * p or ib <= ia:
                    continue
                inside = qs[ia + 1:ib]                         # hidden sheets seen by the judge
                m = len(inside)
                if m == 0:
                    packs.append(dict(judge=judge, n=n, m=0, err=[], null=[], p=p))
                    continue
                # map the pack linearly onto the judge's interval (bounds may drift)
                pred_j = qs[ia] + (pred - rs[a]) * (qs[ib] - qs[ia]) / g
                err = [np.min(np.abs(pred_j - x)) for x in inside]
                nul = []
                for _ in range(5):
                    rp = np.sort(rng.uniform(qs[ia], qs[ib], n - 1))
                    nul.extend(np.min(np.abs(rp - x)) for x in inside)
                packs.append(dict(judge=judge, n=n, m=m, err=err, null=nul, p=p))
print(f"packs x judges: {len(packs)}  [{time.time()-t0:.0f}s]")


def report(judge):
    P = [q for q in packs if q["judge"] == judge]
    n_ = np.array([q["n"] for q in P]); m_ = np.array([q["m"] for q in P])
    seen = m_ > 0
    print(f"\n--- judge: neighbouring {judge} ---")
    print(f"  packs: {len(P)}; with >= 1 hidden sheet seen by the judge: {seen.sum()} "
          f"({seen.mean():.0%}); layers predicted per pack: median {np.median(n_-1):.0f}, max {n_.max()-1}")
    e1 = (m_ <= n_ - 1).mean()
    print(f"  E1 count  - judge sees no more sheets than predicted layers: {e1:.0%} "
          f"-> {'PASS' if e1 >= 0.90 else 'FAIL'}")
    err = np.concatenate([np.array(q["err"]) / q["p"] for q in P if q["m"]])
    nul = np.concatenate([np.array(q["null"]) / q["p"] for q in P if q["m"]])
    ratio = np.median(err) / np.median(nul)
    boots = []
    idx = [k for k, q in enumerate(P) if q["m"]]
    for _ in range(200):
        s = rng.choice(idx, len(idx), replace=True)
        e_ = np.concatenate([np.array(P[k]["err"]) / P[k]["p"] for k in s])
        n2 = np.concatenate([np.array(P[k]["null"]) / P[k]["p"] for k in s])
        boots.append(np.median(e_) / np.median(n2))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    e2 = ratio < 0.6 and hi < 0.6
    print(f"  E2 position - median |error| {np.median(err):.2f} pitch (= {np.median(err)*np.median([q['p'] for q in P])*VOX*1000:.0f} um) "
          f"vs random {np.median(nul):.2f} pitch; ratio {ratio:.2f} [CI95 {lo:.2f}, {hi:.2f}] "
          f"-> {'PASS' if e2 else 'FAIL'}")
    within = (err < 0.25).mean()
    print(f"  hidden sheets landing within a quarter pitch of a predicted layer: {within:.0%} "
          f"(random would give ~{(nul < 0.25).mean():.0%})")
    # count agreement when the judge sees sheets
    print(f"  count check where judge sees sheets: m = n-1 in {(m_[seen] == n_[seen]-1).mean():.0%}, "
          f"m < n-1 in {(m_[seen] < n_[seen]-1).mean():.0%}, m > n-1 in {(m_[seen] > n_[seen]-1).mean():.0%}")
    return e1, e2, err, nul, n_, m_

r_plane = report("plane")
r_ray = report("ray")
verdict = ("COMPATIBLE - equal layers predict where the hidden sheets are" if r_plane[0] >= 0.90 and r_plane[1]
           else "NOT COMPATIBLE" if not r_plane[1] else "N WRONG - judge sees more sheets than layers")
print(f"\nVERDICT (plane judge): {verdict}")

np.savez("layer_division_1218.npz", err_plane=r_plane[2], null_plane=r_plane[3],
         err_ray=r_ray[2], null_ray=r_ray[3], n_plane=r_plane[4], m_plane=r_plane[5], verdict=verdict)
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
ax[0].hist(r_plane[2], bins=40, range=(0, 0.5), alpha=.7, label="equal layers")
ax[0].hist(r_plane[3], bins=40, range=(0, 0.5), alpha=.5, label="random positions", density=False,
           weights=np.full(len(r_plane[3]), len(r_plane[2]) / len(r_plane[3])))
ax[0].set_xlabel("|predicted - labelled| (fraction of pitch), plane judge"); ax[0].legend()
ax[0].set_title("E2: prediction error vs chance")
nm = r_plane[4] - 1; mm = r_plane[5]; seen = mm > 0
ax[1].scatter(nm[seen] + rng.normal(0, .08, seen.sum()), mm[seen] + rng.normal(0, .08, seen.sum()), s=6, alpha=.4)
mx = max(nm.max(), mm.max()) + 1; ax[1].plot([0, mx], [0, mx], "g--")
ax[1].set_xlabel("layers predicted (n-1)"); ax[1].set_ylabel("hidden sheets the judge sees (m)")
ax[1].set_title("E1: never more sheets than layers")
plt.tight_layout(); plt.savefig("layer_division_1218.png", dpi=130)
print(f"saved layer_division_1218.npz / .png  [{time.time()-t0:.0f}s]")

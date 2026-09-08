#!/usr/bin/env python3
"""
mass_count_1218.py — COUNT THE SHEETS IN A PACK BY THEIR MASS, NOT THEIR PITCH.

PREMISE (Diego, 7 Sep). A quality papyrus carries the same amount of material
per sheet everywhere. A pressed pack has less pitch but the same mass per
sheet, so   n = mass(pack) / mass(one sheet).

WHAT IS MEASURED (CT level 1, 17.28 um). Along the ray, brightness above the
local air level is summed:
  mass(pack)      over the gap between the two labelled sheets bounding it
                  (each half-sheet at the ends counts half: together, one)
  mass(one sheet) the same sum over the NORMAL gaps adjacent to the pack in
                  the same column (each holds exactly one sheet-equivalent);
                  median of up to 3 per side
  n_mass = round(mass(pack) / mass(one sheet)),  n_pitch = round(g / p_healthy)
JUDGE. As in layer_division / layer_compression: the same ray one plane up and
down; the sheets it sees inside the matched interval. Odd planes only (the
even planes were used for calibration in layer_compression; here nothing is
calibrated on the table, but the split is kept for comparability).
EXAM, same thresholds as before, both counts on the SAME packs:
  E1 count: judge never sees more sheets than layers in >= 90 % of packs
  exact agreement (m == n-1 where the judge sees sheets) — the gain of mass
  over pitch is the number to read
  E2 position: equal layers at n_mass; ratio to random < 0.6
TWIN (mass_count_twin_1218.py): pressed packs (pitch x0.6, same mass) ->
  pitch count under-counts, mass count PASSES; uniform packs -> both pass.
COST. N_PACKS small CT boxes; ~15-30 min on Colab.
OUTPUT. mass_count_1218.npz / .png
"""
if "rows" not in dir():
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)) if "__file__" in dir() else "scripts")
    from pherc1218_io import load_all
    globals().update(load_all(ct=False))
if "ct_root" not in dir():
    from pherc1218_io import open_ct_root
    ct_root = open_ct_root()
if "origins_ct" not in dir():
    from pherc1218_io import load_origins
    origins_ct = load_origins(zs, toward_ct=True)

import numpy as np, matplotlib.pyplot as plt, time
t0 = time.time()
VOX = 0.01728; GAP_MIN = 1.6; N_PACKS = 3000
rng = np.random.default_rng(1218)
L1 = ct_root["1"]

kmax = max(int(r["k"]) for r in rows); nzp = len(zs)
Rg = np.full((kmax + 1, 60, nzp), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]), int(round(float(r["theta_deg"]) / 6)) % 60, zpos[int(r["z"])]] = float(r["r_l1_vox"])
cols = {(i, iz): np.sort(Rg[:, i, iz][np.isfinite(Rg[:, i, iz])]) for iz in range(nzp) for i in range(60)}

# ---- enumerate packs on odd planes with a judge and >= 2 normal gaps nearby --
packs = []
for iz in range(1, nzp, 2):
    for i in range(60):
        rs = cols[(i, iz)]
        if len(rs) < 6:
            continue
        d = np.diff(rs); m_all = np.median(d)
        normal = (d > 0.5 * m_all) & (d < 1.5 * m_all)
        for a in range(len(rs) - 1):
            g = d[a]
            near = [b for b in list(range(a - 3, a)) + list(range(a + 1, a + 4)) if 0 <= b < len(d) and normal[b]]
            if len(near) < 2:
                continue
            ph = float(np.median(d[near]))
            if g < GAP_MIN * ph:
                continue
            judges = []
            for j_iz in (iz - 1, iz + 1):
                if not (0 <= j_iz < nzp):
                    continue
                qs = cols[(i, j_iz)]
                if len(qs) < 4:
                    continue
                ia = np.argmin(np.abs(qs - rs[a])); ib = np.argmin(np.abs(qs - rs[a + 1]))
                if abs(qs[ia] - rs[a]) > 0.5 * ph or abs(qs[ib] - rs[a + 1]) > 0.5 * ph or ib <= ia:
                    continue
                judges.append((qs[ia], qs[ib], qs[ia + 1:ib]))
            if judges:
                packs.append(dict(i=i, iz=iz, a=a, rs=rs, near=near, g=g, ph=ph, judges=judges))
print(f"packs with a judge on odd planes: {len(packs)}")
sel = rng.choice(len(packs), min(N_PACKS, len(packs)), replace=False)
print(f"sampling {len(sel)} of them for the CT  [{time.time()-t0:.0f}s]")


def ray_profile(z, cx, cy, theta, r0, r1):
    """brightness along the ray between radii r0..r1 (level-1 voxels, step 1)"""
    a = np.radians(theta); rr = np.arange(r0, r1 + 1, 1.0)
    xs = cx + rr * np.cos(a); ys = cy + rr * np.sin(a)
    x0, x1 = int(xs.min()) - 1, int(xs.max()) + 2; y0, y1 = int(ys.min()) - 1, int(ys.max()) + 2
    if min(x0, y0) < 0:
        return None, None
    img = np.asarray(L1[int(z), y0:y1, x0:x1]).astype(np.float32)
    if img.size == 0:
        return None, None
    px = np.clip(xs.astype(int) - x0, 0, img.shape[1] - 1); py = np.clip(ys.astype(int) - y0, 0, img.shape[0] - 1)
    return rr, img[py, px]


def mass_between(rr, prof, air, r0, r1):
    m = (rr >= r0) & (rr <= r1)
    return float(np.sum(np.clip(prof[m] - air, 0, None)))


recs = []
for c_, k in enumerate(sel):
    q = packs[k]; z = zs[q["iz"]]; cx, cy = origins_ct[z]
    rs, a = q["rs"], q["a"]
    lo = min(rs[max(0, a - 3)], rs[a]) - 3; hi = max(rs[min(len(rs) - 1, a + 4)], rs[a + 1]) + 3
    rr, prof = ray_profile(z, cx, cy, q["i"] * 6.0, lo, hi)
    if rr is None:
        continue
    air = float(np.percentile(prof, 5))
    m1 = np.median([mass_between(rr, prof, air, rs[b], rs[b + 1]) for b in q["near"]])
    if m1 <= 0:
        continue
    m_pack = mass_between(rr, prof, air, rs[a], rs[a + 1])
    n_mass = max(2, int(round(m_pack / m1)))
    n_pitch = max(2, int(round(q["g"] / q["ph"])))
    recs.append(dict(q=q, n_mass=n_mass, n_pitch=n_pitch, ratio=m_pack / m1, g_p=q["g"] / q["ph"]))
    if c_ % 300 == 0:
        print(f"  {c_}/{len(sel)}  [{time.time()-t0:.0f}s]")
print(f"packs measured: {len(recs)}  [{time.time()-t0:.0f}s]")


def evaluate(which):
    err, nul, over, agree, tot, seen_n = [], [], 0, 0, 0, 0
    for rec in recs:
        q = rec["q"]; n = rec[which]; rs, a = q["rs"], q["a"]
        pred = rs[a] + q["g"] * np.arange(1, n) / n
        for qa, qb, inside in q["judges"]:
            tot += 1; mm = len(inside)
            over += mm > n - 1
            if mm:
                seen_n += 1; agree += mm == n - 1
                pj = qa + (pred - rs[a]) * (qb - qa) / q["g"]
                err.append(np.median([np.min(np.abs(pj - x)) / q["ph"] for x in inside]))
                rp = np.sort(rng.uniform(qa, qb, n - 1))
                nul.append(np.median([np.min(np.abs(rp - x)) / q["ph"] for x in inside]))
    err, nul = np.array(err), np.array(nul)
    ratio = np.median(err) / np.median(nul)
    b = [np.median(err[s]) / np.median(nul[s]) for s in (rng.integers(0, len(err), len(err)) for _ in range(300))]
    return dict(e1=1 - over / tot, agree=agree / max(seen_n, 1), err=float(np.median(err)),
                ratio=ratio, ci=np.percentile(b, [2.5, 97.5]), n=tot, seen=seen_n)


res = {w: evaluate(w) for w in ("n_pitch", "n_mass")}
for w, lab in (("n_pitch", "PITCH count (baseline)"), ("n_mass", "MASS count")):
    e = res[w]
    print(f"\nEXAM — {lab}: {e['n']} pack-judge pairs, judge sees sheets in {e['seen']}")
    print(f"  E1 count   never more sheets than layers: {e['e1']:.1%} -> {'PASS' if e['e1'] >= 0.90 else 'FAIL'}; "
          f"judge-count matches exactly (informative only, judge is incomplete): {e['agree']:.0%}")
    print(f"  E2 position median error {e['err']:.2f} pitch, ratio to random {e['ratio']:.2f} "
          f"[CI95 {e['ci'][0]:.2f}, {e['ci'][1]:.2f}] -> {'PASS' if e['ci'][1] < 0.6 else 'FAIL'}")
# the judge is a LOWER bound (it misses hidden sheets), so "exact agreement"
# rewards under-counting; the verdict rests on E1 (never over) and E2 (position)
pm, pp = res["n_mass"], res["n_pitch"]
mass_ok = pm["e1"] >= 0.90 and pm["ci"][1] < 0.6
pitch_ok = pp["e1"] >= 0.90 and pp["ci"][1] < 0.6
better = pm["ratio"] < 0.8 * pp["ratio"]
if mass_ok and (not pitch_ok or better):
    v = "MASS COUNTS THE SHEETS - the premise holds; mass beats the pitch count"
elif mass_ok and pitch_ok:
    v = "NO DIFFERENCE - both pass; CT mass adds little over the pitch"
elif not mass_ok and pitch_ok:
    v = "MASS IS WORSE - mass per sheet is not constant (premise fails)"
else:
    v = "NEITHER PASSES - packs are not equal layers by mass nor by pitch"
print(f"\nVERDICT: {v}")
print(f"  position error pitch {pp['err']:.2f} -> mass {pm['err']:.2f} (fraction of pitch); "
      f"over-count pitch {1-pp['e1']:.1%} -> mass {1-pm['e1']:.1%}")
rat = np.array([r["ratio"] for r in recs]); gp = np.array([r["g_p"] for r in recs])
print(f"mass ratio vs pitch ratio per pack: median mass/pitch = {np.median(rat/gp):.2f} "
      f"(1 = packs hold the same material per unit length as free sheets)")
np.savez("mass_count_1218.npz", ratio=rat, g_p=gp, res=str(res), verdict=v)
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
ax[0].scatter(gp, rat, s=5, alpha=.4); ax[0].plot([1, 8], [1, 8], "g--")
ax[0].set_xlabel("pack gap / healthy pitch"); ax[0].set_ylabel("pack mass / one-sheet mass")
ax[0].set_title("packs: mass vs pitch"); ax[0].set_xlim(1, 8); ax[0].set_ylim(0, 10)
ax[1].hist(rat / gp, bins=40, range=(0.3, 2)); ax[1].axvline(1, color="k", lw=.7)
ax[1].set_xlabel("material density in pack relative to free sheets")
plt.tight_layout(); plt.savefig("mass_count_1218.png", dpi=130)
print(f"saved mass_count_1218.npz / .png  [{time.time()-t0:.0f}s]")

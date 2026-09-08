#!/usr/bin/env python3
"""
layer_compression_1218.py — HOW MUCH ARE SHEETS PRESSED INSIDE A PACK, WHERE,
AND DOES KNOWING IT FIX THE LAYER COUNT?

FOLLOWS layer_division_1218.py (7 Sep): equal layers at the column's normal
pitch put the hidden sheets 35 um from where the neighbouring plane sees them
(twice better than chance) but in 15 % of packs the judge sees MORE sheets
than layers: inside a pack the pitch is shorter than in the free sheets.

TWO PITCHES PER PACK (Diego's framing):
  p_healthy  median of the normal gaps adjacent to the pack in the same
             column (up to 3 on each side)
  p_inside   from the judge planes (same ray, one plane up and down): the
             matched interval divided by (m+1), taking the judge that sees
             the most sheets. A judge can miss sheets, so p_inside is an
             UPPER bound and c = p_inside / p_healthy is biased toward 1.
CALIBRATION / EXAM SPLIT: even planes calibrate, odd planes examine.
  Calibration: median c per zone = (angle bin of 30 deg) x (radial third).
  Exam, on odd-plane packs only, two predictions compared on the SAME packs:
    baseline  n = round(g / p_healthy)
    corrected n = round(g / (c_zone * p_healthy))
  E1 count: judge never sees more sheets than layers, in >= 90 % of packs
  E2 position: median error / random error < 0.6 (bootstrap CI95)
  plus the gain: how many packs move from "judge sees more than layers"
  to agreement.
OUTPUT. layer_compression_1218.npz, layer_compression_1218.png (the map)
INPUT. crossing table only. ~2 min.
"""
if "rows" not in dir():
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)) if "__file__" in dir() else "scripts")
    from pherc1218_io import load_all
    globals().update(load_all(ct=False))

import numpy as np, matplotlib.pyplot as plt, time
t0 = time.time()
VOX = 0.01728; GAP_MIN = 1.6
rng = np.random.default_rng(11)

kmax = max(int(r["k"]) for r in rows); nzp = len(zs)
Rg = np.full((kmax + 1, 60, nzp), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]), int(round(float(r["theta_deg"]) / 6)) % 60, zpos[int(r["z"])]] = float(r["r_l1_vox"])
cols = {(i, iz): np.sort(Rg[:, i, iz][np.isfinite(Rg[:, i, iz])]) for iz in range(nzp) for i in range(60)}
r_edge = np.nanmax(Rg)          # outermost labelled radius (for radial thirds)

packs = []
for iz in range(nzp):
    for i in range(60):
        rs = cols[(i, iz)]
        if len(rs) < 6:
            continue
        d = np.diff(rs); m_all = np.median(d)
        normal = (d > 0.5 * m_all) & (d < 1.5 * m_all)
        for a in range(len(rs) - 1):
            g = d[a]
            # healthy pitch: normal gaps adjacent to the pack, up to 3 per side
            near = [d[b] for b in list(range(a - 3, a)) + list(range(a + 1, a + 4))
                    if 0 <= b < len(d) and normal[b]]
            if len(near) < 2:
                continue
            ph = float(np.median(near))
            if g < GAP_MIN * ph:
                continue
            # judges: same ray, plane above and below
            best_m, best_int = -1, None; judges = []
            for j_iz in (iz - 1, iz + 1):
                if not (0 <= j_iz < nzp):
                    continue
                qs = cols[(i, j_iz)]
                if len(qs) < 4:
                    continue
                ia = np.argmin(np.abs(qs - rs[a])); ib = np.argmin(np.abs(qs - rs[a + 1]))
                if abs(qs[ia] - rs[a]) > 0.5 * ph or abs(qs[ib] - rs[a + 1]) > 0.5 * ph or ib <= ia:
                    continue
                inside = qs[ia + 1:ib]
                judges.append((qs[ia], qs[ib], inside))
                if len(inside) > best_m:
                    best_m, best_int = len(inside), (qs[ia], qs[ib])
            if not judges:
                continue
            p_in = (best_int[1] - best_int[0]) / (best_m + 1) if best_m >= 0 else np.nan
            packs.append(dict(i=i, iz=iz, r=(rs[a] + rs[a + 1]) / 2, g=g, ph=ph,
                              m=best_m, p_in=p_in, judges=judges))
print(f"packs with a judge: {len(packs)}  [{time.time()-t0:.0f}s]")

I = np.array([q["i"] for q in packs]); IZ = np.array([q["iz"] for q in packs])
R = np.array([q["r"] for q in packs]); G = np.array([q["g"] for q in packs])
PH = np.array([q["ph"] for q in packs]); M = np.array([q["m"] for q in packs])
PIN = np.array([q["p_in"] for q in packs])
C = PIN / PH                                    # compression factor (upper bound)
seen = M > 0
zone_a = (I * 6 // 30) % 12                     # 12 angle bins of 30 deg
zone_r = np.minimum((R / r_edge * 3).astype(int), 2)   # radial third
calib = (IZ % 2 == 0)

# ---- calibration map on even planes, packs where the judge sees sheets ----
cmap = np.full((12, 3), np.nan); nmap = np.zeros((12, 3), int)
for za in range(12):
    for zr in range(3):
        s = calib & seen & (zone_a == za) & (zone_r == zr)
        nmap[za, zr] = s.sum()
        if s.sum() >= 30:
            cmap[za, zr] = np.median(C[s])
c_global = float(np.median(C[calib & seen]))
print(f"\nCOMPRESSION (calibration, even planes, judge sees >= 1 sheet): "
      f"global median c = {c_global:.2f}  (pitch inside a pack = c x healthy pitch; upper bound)")
print(f"  by radial third (inner/middle/outer): "
      + " / ".join(f"{np.nanmedian(C[calib & seen & (zone_r == t)]):.2f}" for t in range(3)))
print("  by angle (30 deg bins, all depths): "
      + " ".join(f"{a*30:3d}:{np.nanmedian(C[calib & seen & (zone_a == a)]):.2f}" for a in range(12)))


def c_of(za, zr):
    v = cmap[za, zr]
    return v if np.isfinite(v) else c_global


# ---- exam on odd planes: baseline vs corrected --------------------------------
def evaluate(use_c):
    err, nul, over, agree, tot = [], [], 0, 0, 0
    for k in np.flatnonzero(~calib):
        q = packs[k]
        pitch = q["ph"] * (c_of(zone_a[k], zone_r[k]) if use_c else 1.0)
        n = max(2, int(round(q["g"] / pitch)))
        pred = q["r"] - q["g"] / 2 + q["g"] * np.arange(1, n) / n
        for qa, qb, inside in q["judges"]:
            tot += 1
            mm = len(inside)
            if mm > n - 1:
                over += 1
            if mm == n - 1:
                agree += 1
            if mm == 0:
                continue
            pj = qa + (pred - (q["r"] - q["g"] / 2)) * (qb - qa) / q["g"]
            e = [np.min(np.abs(pj - x)) / q["ph"] for x in inside]
            err.append(np.median(e))
            rp = np.sort(rng.uniform(qa, qb, n - 1))
            nul.append(np.median([np.min(np.abs(rp - x)) / q["ph"] for x in inside]))
    err, nul = np.array(err), np.array(nul)
    ratio = np.median(err) / np.median(nul)
    b = [np.median(err[s]) / np.median(nul[s]) for s in (rng.integers(0, len(err), len(err)) for _ in range(200))]
    return dict(e1=1 - over / tot, agree=agree / tot, err=float(np.median(err)), ratio=ratio,
                ci=np.percentile(b, [2.5, 97.5]), n=tot)


base = evaluate(False); corr = evaluate(True)
for name, e in (("baseline (healthy pitch)", base), ("corrected (zone compression)", corr)):
    print(f"\nEXAM on odd planes — {name}: {e['n']} pack-judge pairs")
    print(f"  E1 count   never more sheets than layers: {e['e1']:.1%} -> {'PASS' if e['e1'] >= 0.90 else 'FAIL'}; "
          f"exact agreement {e['agree']:.0%}")
    print(f"  E2 position median error {e['err']:.2f} pitch, ratio to random {e['ratio']:.2f} "
          f"[CI95 {e['ci'][0]:.2f}, {e['ci'][1]:.2f}] -> {'PASS' if e['ci'][1] < 0.6 else 'FAIL'}")
gain = corr["e1"] - base["e1"]
verdict = ("COMPRESSION FIXES THE COUNT" if corr["e1"] >= 0.90 and corr["ci"][1] < 0.6 and gain > 0
           else "COMPRESSION HELPS BUT COUNT STILL FAILS" if gain > 0.01
           else "NO GAIN FROM ZONE COMPRESSION")
print(f"\nVERDICT: {verdict}  (E1 gain {gain:+.1%}, agreement {base['agree']:.0%} -> {corr['agree']:.0%})")

np.savez("layer_compression_1218.npz", cmap=cmap, nmap=nmap, c_global=c_global, C=C, I=I, IZ=IZ, R=R, M=M,
         base=str(base), corr=str(corr), verdict=verdict)
fig = plt.figure(figsize=(11, 4.5))
ax = fig.add_subplot(1, 2, 1, projection="polar")
th = np.radians(np.arange(12) * 30 + 15)
for zr, lab in enumerate(("inner", "middle", "outer")):
    ax.plot(np.r_[th, th[0]], np.r_[cmap[:, zr], cmap[0, zr]], "o-", ms=3, label=lab)
ax.set_title("compression c by angle and depth"); ax.legend(loc="lower left", fontsize=7)
ax2 = fig.add_subplot(1, 2, 2)
ax2.hist(C[seen & np.isfinite(C)], bins=40, range=(0.2, 1.4))
ax2.axvline(1, color="k", lw=.7); ax2.set_xlabel("c = pitch inside pack / healthy pitch")
ax2.set_title(f"all packs with a seen sheet; median {np.median(C[seen]):.2f}")
plt.tight_layout(); plt.savefig("layer_compression_1218.png", dpi=130)
print(f"saved layer_compression_1218.npz / .png  [{time.time()-t0:.0f}s]")

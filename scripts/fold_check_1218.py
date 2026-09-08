#!/usr/bin/env python3
"""
fold_check_1218.py — WHICH CROSSINGS ARE FOLDS OF THE SAME SHEET, NOT SEPARATE WINDINGS?

THE PROBLEM (Diego, 8 Sep: "a surfboard cutting several waves of the same
water"). A horizontal slice cuts a sheet once where the sheet runs straight,
but where the sheet undulates in height the slice cuts it two or more times,
and neighbouring crossings on a ray can be the SAME winding. Mode 20 counts
crossings; this script asks which of them are windings.

WHAT IT CAN AND CANNOT SEE. A wave-fold crossing pair moves as the plane
changes: going up or down, the two crossings approach, meet and vanish (the
plane stops touching that wave). Two windings keep their spacing plane after
plane. So tracking each crossing through neighbouring planes separates the
two. A fold that runs the whole height of the roll as a crease (a Z-fold at a
hinge) does not vanish with height and is NOT separable this way — a stated
limit.

METHOD. Per ray, the column of crossings on each plane = labelled (split
labels merged) + predicted hidden (mode 20 rule). Crossings are linked plane
to plane by nearest radius within 0.5 x local pitch, forming tracks along z.
For every adjacent pair on a plane, the separation s(z) is followed over
+/- W planes. The pair is a FOLD CANDIDATE if, within the window, either
  (a) s drops below FOLD_FRAC x pitch, or shrinks to < CLOSE_FRAC of its
      starting value (the pair closes), or
  (b) one track ends while the other continues AND the pair was closing.
Split labels are merged first (< 7 vox), so a fold pair near its apex is
already one crossing; that is why (b) is needed.
Each crossing is flagged if it belongs to a fold-candidate pair on the side
where the convergence happens.

TWIN (fold_check_twin_1218.py). Straight windings plus planted wave folds
(parabolic pairs that meet at an apex). Target: >= 80 % of planted fold
crossings flagged, <= 5 % of true windings flagged.
RESULT (8 Sep, three versions): 38-60 % caught, 7-11 % false. NOT GOOD ENOUGH
to certify crossings one by one; kept as a map of fold-prone zones only. The
per-voxel label tree sees a wave as one surface directly; that is where this
question belongs (see mode 20, "Limit: folds").

OUTPUT. fold_check_1218.npz, fold_check_1218.png, and the fraction of
predicted hidden crossings that are fold candidates (the number to read).
"""
if "rows" not in dir():
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)) if "__file__" in dir() else "scripts")
    from pherc1218_io import load_all
    globals().update(load_all(ct=False))

import numpy as np, matplotlib.pyplot as plt, time
t0 = time.time()
VOX = 0.01728; GAP_MIN = 1.6; SPLIT_TOL = 7.0
W = 6                  # planes followed each side (6 x 0.55 mm = 3.3 mm)
FOLD_FRAC = 0.4        # separation below this x pitch = converging
CLOSE_FRAC = 0.65      # a pair whose separation shrinks below this fraction of its start is closing
LINK_FRAC = 0.7        # link tolerance between planes, x pitch (fold crossings move fast)

kmax = max(int(r["k"]) for r in rows); nzp = len(zs)
Rg = np.full((kmax + 1, 60, nzp), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]), int(round(float(r["theta_deg"]) / 6)) % 60, zpos[int(r["z"])]] = float(r["r_l1_vox"])


def merged(rs):
    out, grp = [], [rs[0]]
    for x in rs[1:]:
        if x - grp[-1] < SPLIT_TOL:
            grp.append(x)
        else:
            out.append(np.mean(grp)); grp = [x]
    out.append(np.mean(grp)); return np.array(out)


# ---- columns: labelled (merged) + predicted, with a flag per crossing ----
cols = {}          # (i, iz) -> (r sorted, is_pred, pitch)
for iz in range(nzp):
    for i in range(60):
        rs = Rg[:, i, iz]; rs = np.sort(rs[np.isfinite(rs)])
        if len(rs) < 6:
            continue
        rs = merged(rs); d = np.diff(rs); m_all = np.median(d)
        normal = (d > 0.5 * m_all) & (d < 1.5 * m_all)
        pred = []
        for a in range(len(rs) - 1):
            near = [d[b] for b in list(range(a - 3, a)) + list(range(a + 1, a + 4)) if 0 <= b < len(d) and normal[b]]
            if len(near) < 2:
                continue
            p = float(np.median(near)); g = d[a]
            if g >= GAP_MIN * p and int(round(g / p)) >= 2:
                n = int(round(g / p)); pred += [rs[a] + g * j / n for j in range(1, n)]
        allr = np.r_[rs, pred]; flag = np.r_[np.zeros(len(rs), bool), np.ones(len(pred), bool)]
        o = np.argsort(allr)
        cols[(i, iz)] = (allr[o], flag[o], float(np.median(d[normal])) if normal.any() else m_all)
print(f"columns: {len(cols)}  [{time.time()-t0:.0f}s]")


def link(i, iz, r, step):
    """radius of the nearest crossing on plane iz+step within LINK_FRAC x pitch, or nan"""
    key = (i, iz + step)
    if key not in cols:
        return np.nan
    rr, _, p = cols[key]; j = np.searchsorted(rr, r)
    best = np.nan; bd = LINK_FRAC * p
    for c in (j - 1, j):
        if 0 <= c < len(rr) and abs(rr[c] - r) < bd:
            bd = abs(rr[c] - r); best = rr[c]
    return best


def track(i, iz, r, direction):
    """follow a crossing up (+1) or down (-1) for up to W planes; list of radii (nan when lost)"""
    out = []; cur = r
    for s in range(1, W + 1):
        cur = link(i, iz + (s - 1) * direction, cur, direction) if s == 1 or np.isfinite(cur) else np.nan
        out.append(cur)
        if not np.isfinite(cur):
            break
    return out


fold_flag = {}     # (i, iz) -> bool array per crossing
n_pairs = n_fold = 0
for (i, iz), (rr, isp, p) in cols.items():
    f = np.zeros(len(rr), bool)
    for a in range(len(rr) - 1):
        ra, rb = rr[a], rr[a + 1]; s0 = rb - ra
        converge = False; lost_a = lost_b = False; seps = [s0]; drift_a = drift_b = 0.0
        for direction in (+1, -1):
            ta = track(i, iz, ra, direction); tb = track(i, iz, rb, direction)
            fa = [x for x in ta if np.isfinite(x)]; fb = [x for x in tb if np.isfinite(x)]
            if fa: drift_a = max(drift_a, abs(fa[-1] - ra))
            if fb: drift_b = max(drift_b, abs(fb[-1] - rb))
            for k in range(max(len(ta), len(tb))):
                xa = ta[k] if k < len(ta) else np.nan; xb = tb[k] if k < len(tb) else np.nan
                if np.isfinite(xa) and np.isfinite(xb):
                    seps.append(xb - xa)
                    if xb - xa < FOLD_FRAC * p:
                        converge = True
                else:
                    # one continues, the other is lost while the pair was closer than a pitch
                    if np.isfinite(xa) != np.isfinite(xb) and seps[-1] < 0.8 * p:
                        if np.isfinite(xa):
                            lost_b = True
                        else:
                            lost_a = True
                    break
        seps = np.array(seps)
        closing = seps.min() < CLOSE_FRAC * seps[0]      # the pair closes by >= (1-CLOSE_FRAC)
        n_pairs += 1
        if (converge or closing) and (converge or seps[0] < 1.3 * p):
            # the fold crossing is the one that MOVES; a winding keeps its radius
            if drift_a > 2.0 * drift_b + 1.0:
                f[a] = True
            elif drift_b > 2.0 * drift_a + 1.0:
                f[a + 1] = True
            else:
                f[a] = f[a + 1] = True
            n_fold += 1
        elif (lost_a or lost_b) and closing:
            # a crossing lost within W planes while its pair was closing: a wave apex
            f[a] |= lost_a; f[a + 1] |= lost_b; n_fold += 1
    fold_flag[(i, iz)] = f

allp = np.concatenate([cols[k][1] for k in cols]); allf = np.concatenate([fold_flag[k] for k in cols])
print(f"\ncrossings: {len(allp):,} ({allp.sum():,} predicted hidden); adjacent pairs: {n_pairs:,}, "
      f"fold-candidate pairs: {n_fold:,} ({n_fold/n_pairs:.1%})  [{time.time()-t0:.0f}s]")
print(f"FOLD CANDIDATES - among labelled crossings: {allf[~allp].mean():.1%}; "
      f"among predicted hidden crossings: {allf[allp].mean():.1%}")
# by depth
r_all = np.concatenate([cols[k][0] for k in cols]); r_edge = r_all.max()
for t_, lab in enumerate(("inner", "middle", "outer")):
    s = (r_all >= t_ * r_edge / 3) & (r_all < (t_ + 1) * r_edge / 3)
    print(f"  {lab} third: labelled {allf[s & ~allp].mean():.1%}, predicted {allf[s & allp].mean():.1%}")
np.savez("fold_check_1218.npz", frac_lab=allf[~allp].mean(), frac_pred=allf[allp].mean(), W=W, FOLD_FRAC=FOLD_FRAC)
fig, ax = plt.subplots(figsize=(7, 4))
za = np.array([k[1] for k in cols for _ in range(len(cols[k][0]))]) * 0 + 0
fr = [allf[np.concatenate([np.full(len(cols[k][0]), k[1] == iz) for k in cols])].mean() for iz in range(nzp)]
ax.plot(np.array(zs) * VOX, fr); ax.set_xlabel("height (mm)"); ax.set_ylabel("fraction of crossings flagged as fold")
ax.set_title(f"fold candidates: labelled {allf[~allp].mean():.1%}, predicted {allf[allp].mean():.1%}")
plt.tight_layout(); plt.savefig("fold_check_1218.png", dpi=130)
print(f"saved fold_check_1218.npz / .png  [{time.time()-t0:.0f}s]")

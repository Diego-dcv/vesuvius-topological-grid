#!/usr/bin/env python3
"""
hidden_sheets_1218.py — THE LIST OF HIDDEN SHEETS, AND WHETHER THE SCAN AGREES.

Built on the week's result (layer_division / layer_compression / mass_count,
6-8 Sep): between two labelled sheets on a ray, a gap wider than 1.6x the
local pitch holds sheets at the NORMAL pitch, equally spaced; the neighbouring
plane's labels confirm it (median error 35 um; with split labels merged the
judge sees more sheets than predicted in only 2 % of packs). Neither pressing
(mass) nor zone compression exists.

STEP 1 (table only): on every ray of every plane, merge split labels (< 7 vox
apart), take the local pitch from the normal gaps, find the packs, and place
the hidden sheets at equal division. Output: one row per predicted sheet
(z, theta_deg, r_vox, r_um, k_inner, k_outer, n_in_pack). Also the hidden
length per plane (each prediction stands for 6 deg of arc at its radius) next
to the labelled length, so the roll's book-keeping closes: labelled + hidden
+ lost = loom.

STEP 2 (CT level 1, only if ct_root is available): at every predicted position
the brightness (max over r +/- 1.5 vox) is compared with the material
threshold used by the wedge audit (p5 of the brightness on labelled sheets).
Control: the same test at the labelled sheets themselves (must be ~100 %) and
at random radii inside known VOIDS is not available, so the second control is
the midpoints between predicted sheets (should be lower, or equal if fused).
Output: the same list with a material flag; summary of how many predicted
sheets sit on material.

OUTPUT. hidden_sheets_1218.csv, hidden_sheets_1218_summary.json,
hidden_sheets_1218.png
"""
if "rows" not in dir():
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)) if "__file__" in dir() else "scripts")
    from pherc1218_io import load_all
    globals().update(load_all(ct=False))

import numpy as np, matplotlib.pyplot as plt, time, json, csv
t0 = time.time()
VOX = 0.01728; GAP_MIN = 1.6; SPLIT_TOL = 7.0
HAVE_CT = "ct_root" in dir()

kmax = max(int(r["k"]) for r in rows); nzp = len(zs)
Rg = np.full((kmax + 1, 60, nzp), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]), int(round(float(r["theta_deg"]) / 6)) % 60, zpos[int(r["z"])]] = float(r["r_l1_vox"])


def merged(rs, ks, tol=SPLIT_TOL):
    out_r, out_k = [], []; gr, gk = [rs[0]], [ks[0]]
    for x, k in zip(rs[1:], ks[1:]):
        if x - gr[-1] < tol:
            gr.append(x); gk.append(k)
        else:
            out_r.append(np.mean(gr)); out_k.append(gk[0]); gr, gk = [x], [k]
    out_r.append(np.mean(gr)); out_k.append(gk[0])
    return np.array(out_r), np.array(out_k)


pred = []           # (iz, i, r, k_in, k_out, n)
lab_len = np.zeros(nzp); hid_len = np.zeros(nzp); packs_per_plane = np.zeros(nzp, int)
for iz in range(nzp):
    for i in range(60):
        col = Rg[:, i, iz]; ks = np.flatnonzero(np.isfinite(col))
        if len(ks) < 6:
            continue
        rs, ks = merged(col[ks], ks)
        lab_len[iz] += np.sum(rs) * VOX * 2 * np.pi / 60          # arc per crossing, mm
        d = np.diff(rs); m_all = np.median(d)
        normal = (d > 0.5 * m_all) & (d < 1.5 * m_all)
        for a in range(len(rs) - 1):
            near = [d[b] for b in list(range(a - 3, a)) + list(range(a + 1, a + 4)) if 0 <= b < len(d) and normal[b]]
            if len(near) < 2:
                continue
            p = float(np.median(near)); g = d[a]
            if g < GAP_MIN * p:
                continue
            n = int(round(g / p))
            if n < 2:
                continue
            packs_per_plane[iz] += 1
            for j in range(1, n):
                rr = rs[a] + g * j / n
                pred.append((iz, i, rr, int(ks[a]), int(ks[a + 1]), n))
                hid_len[iz] += rr * VOX * 2 * np.pi / 60
pred = np.array(pred, dtype=object)
print(f"STEP 1 - predicted hidden sheets: {len(pred):,} on {nzp} planes "
      f"({int(packs_per_plane.sum()):,} packs)  [{time.time()-t0:.0f}s]")
print(f"  labelled length per plane (split labels merged): median {np.median(lab_len)/1000:.2f} m")
print(f"  hidden length per plane at normal pitch:          median {np.median(hid_len)/1000:.2f} m")
print(f"  labelled + hidden:                                 median {np.median(lab_len+hid_len)/1000:.2f} m "
      f"(loom 8.4-9.4 m; the rest is beyond the last labelled sheet or in voids)")

# ---------------- STEP 2: CT check ----------------------------------------------
mat_flag = None
if HAVE_CT:
    from pherc1218_io import load_origins
    origins = load_origins(zs, toward_ct=True, quiet=True)
    L1 = ct_root["1"]; rng = np.random.default_rng(19)
    # material threshold: p5 of brightness at labelled sheets (as in the wedge audit)
    samp = []
    for iz in range(0, nzp, max(1, nzp // 12)):
        z = zs[iz]; cx, cy = origins[z]; sl = np.asarray(L1[z]); H, W = sl.shape
        kk, ii = np.nonzero(np.isfinite(Rg[:, :, iz]))
        for k_, i_ in zip(kk[::7], ii[::7]):
            r = Rg[k_, i_, iz]; a = np.radians(i_ * 6.0)
            x, y = int(round(cx + r * np.cos(a))), int(round(cy + r * np.sin(a)))
            if 0 <= x < W and 0 <= y < H:
                samp.append(float(sl[y, x]))
    UMB = float(np.percentile(samp, 5))
    print(f"STEP 2 - material threshold {UMB:.0f} (p5 on {len(samp)} labelled sheets)")

    def bright(sl, cx, cy, r, a):
        best = 0.0; H, W = sl.shape
        for dr in (-1.5, 0.0, 1.5):
            x, y = int(round(cx + (r + dr) * np.cos(a))), int(round(cy + (r + dr) * np.sin(a)))
            if 0 <= x < W and 0 <= y < H:
                best = max(best, float(sl[y, x]))
        return best

    mat_flag = np.zeros(len(pred), bool); ctrl_lab = []; ctrl_mid = []
    by_plane = {}
    for n_, (iz, i, rr, ka, kb, n) in enumerate(pred):
        by_plane.setdefault(iz, []).append(n_)
    for c_, (iz, idx) in enumerate(sorted(by_plane.items())):
        z = zs[iz]; cx, cy = origins[z]; sl = np.asarray(L1[z])
        for n_ in idx:
            _, i, rr, ka, kb, n = pred[n_]; a = np.radians(i * 6.0)
            mat_flag[n_] = bright(sl, cx, cy, rr, a) >= UMB
        # controls on this plane: labelled sheets, and midpoints between predicted sheets
        kk, ii = np.nonzero(np.isfinite(Rg[:, :, iz]))
        for k_, i_ in zip(kk[::9], ii[::9]):
            ctrl_lab.append(bright(sl, cx, cy, Rg[k_, i_, iz], np.radians(i_ * 6.0)) >= UMB)
        for n_ in idx[::5]:
            _, i, rr, ka, kb, n = pred[n_]
            step = (Rg[kb, i, iz] - Rg[ka, i, iz]) / n
            ctrl_mid.append(bright(sl, cx, cy, rr + step / 2, np.radians(i * 6.0)) >= UMB)
        if c_ % 25 == 0:
            print(f"  plane {c_+1}/{len(by_plane)}  material so far {mat_flag[:max(idx)+1].mean():.0%}  [{time.time()-t0:.0f}s]")
    print(f"STEP 2 - predicted sheets on material: {mat_flag.mean():.1%} of {len(pred):,}")
    print(f"  control, labelled sheets on material: {np.mean(ctrl_lab):.1%}   "
          f"midpoints between predicted sheets: {np.mean(ctrl_mid):.1%}")

# ---------------- outputs ---------------------------------------------------------
with open("hidden_sheets_1218.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["z", "theta_deg", "r_l1_vox", "r_um", "k_inner", "k_outer", "n_in_pack"] + (["material"] if HAVE_CT else []))
    for n_, (iz, i, rr, ka, kb, n) in enumerate(pred):
        w.writerow([zs[iz], i * 6.0, f"{rr:.1f}", f"{rr*VOX*1000:.0f}", ka, kb, n] + ([int(mat_flag[n_])] if HAVE_CT else []))
summary = dict(predicted=int(len(pred)), packs=int(packs_per_plane.sum()),
               labelled_len_m_median=float(np.median(lab_len) / 1000),
               hidden_len_m_median=float(np.median(hid_len) / 1000),
               split_tol_vox=SPLIT_TOL, gap_min=GAP_MIN,
               material_fraction=(float(mat_flag.mean()) if HAVE_CT else None))
json.dump(summary, open("hidden_sheets_1218_summary.json", "w"), indent=1)
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].plot(np.array(zs) * VOX, lab_len / 1000, label="labelled"); ax[0].plot(np.array(zs) * VOX, hid_len / 1000, label="hidden (predicted)")
ax[0].plot(np.array(zs) * VOX, (lab_len + hid_len) / 1000, label="sum", color="k", lw=.8)
ax[0].set_xlabel("height (mm)"); ax[0].set_ylabel("papyrus length per plane (m)"); ax[0].legend()
nn = np.array([p[5] for p in pred]); ax[1].hist(nn - 1, bins=np.arange(0.5, 12.5), rwidth=.8)
ax[1].set_xlabel("hidden sheets per pack"); ax[1].set_title(f"{len(pred):,} hidden sheets")
plt.tight_layout(); plt.savefig("hidden_sheets_1218.png", dpi=130)
print(f"saved hidden_sheets_1218.csv / _summary.json / .png  [{time.time()-t0:.0f}s]")

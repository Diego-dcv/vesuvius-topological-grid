#!/usr/bin/env python3
"""
wedge_fine_1218.py — WEDGES AT THE FINE LEVEL: do the sheets reappear when the
scanner is read at twice the resolution?

WHAT THIS ASKS (plain words). The wedge audit (mode 19, wedge_audit_1218.py)
found that the dead zone of each column still holds material, but only about a
third of the expected sheets can be told apart at 17.28 um/voxel (CT level 1).
Two explanations fit: the sheets are fused (no resolution will separate them),
or they are thinner than the coarse voxel and reappear at 8.64 um (level 0).
This script tells the two apart.

HOW. The wedge audit's lamina counter is run twice on the SAME columns: once on
level 1, once on level 0. Each level calibrates itself on the labelled stretch,
where the number of sheets is known (efficiency eta). Nothing is tuned between
the two runs. ONE DECLARED CHANGE to the audit's counter: its minimum distance
between peaks was 6 coarse voxels (~100 um), which by construction cannot count
sheets packed tighter than that at ANY resolution (found on a synthetic twin
before this run). Here the minimum distance is MIN_PITCH = 2.5 coarse voxels
(~43 um, under one sheet thickness) at both levels, and smoothing is one coarse
voxel wide at both levels; and because a short minimum distance lets scanner
noise fake ridges in a fused slab (also seen on the twin), a ridge must stand
NOISE_K = 5 noise sigmas above its surroundings, sigma measured per column on
the labelled stretch (floor 10, the audit's value). This also means the audit's
rho = 0.34 has a counter floor in it; that is reported, not hidden.

PRE-REGISTERED EXAM (written before the run; no threshold is changed after):
  E1  counter works at the fine level: median eta_0 in [0.3, 1.2] and
      median |eta_0 - eta_1| <= 0.25 on the labelled stretch. If E1 fails, STOP:
      the fine count is not trustworthy and E2 is not read.
  E2a the main question (added after the twin showed level 1 already resolves
      50 um pitches once the counter floor is physical): rho_1 on wedge columns
      with >= 3 expected sheets, rho = (ridges in wedge / eta) / (depth / pitch).
        rho_1 >= 0.60 -> LAMINATED: the sheets are there; the audit's 0.34 was
                         the counter's 100 um floor, not the scroll
        rho_1 <= 0.25 -> FUSED: confirmed with a counter that can see 43 um
        otherwise     -> UNDECIDED
  E2b does the fine level add anything: D = rho_0 - rho_1
        D >= +0.25 and bootstrap CI95 excludes 0  -> YES, resolution mattered
        D <  +0.10                                 -> NO, level 1 suffices
        otherwise                                  -> UNDECIDED
  TWIN (wedge_fine_twin_1218.py, run before this): fused slab -> rho 0.08/0.13,
      E2a FUSED, E2b NO; 52 um sheets -> rho 3.3/3.5, E2a LAMINATED, E2b UNDECIDED.
  C   control: on the labelled stretch, rho-like count at both levels ~1
      (reported, not a gate).

STOP RULE. One run. Whatever comes out is the answer of this experiment.

INPUTS. `rows`, `zs`, `zpos`, `vol` (zarr group root for the 1218 masked
volume: keys "0" fine, "1" coarse) — loaded by pherc1218_io when run
standalone. Level-0 coordinates are 2x level-1 coordinates.

OUTPUTS. cunas_fino_1218.npz (per-column table), cunas_fino_1218.png.
COST. ~20 planes x <=60 rays; reads level 0 in small boxes. Expect 20-40 min
on Colab.
"""

# --- standalone entry: outside the Colab notebook, load the crossing table
# --- and the CT root here. Inside the notebook, where `rows` already exists,
# --- this block does nothing. See scripts/pherc1218_io.py.
if "rows" not in dir():
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)) if "__file__" in dir() else "scripts")
    from pherc1218_io import load_all
    globals().update(load_all(ct=False))
if "ct_root" not in dir():
    from pherc1218_io import open_ct_root
    ct_root = open_ct_root()

import numpy as np, matplotlib.pyplot as plt, time, warnings
from scipy.signal import find_peaks
warnings.filterwarnings("ignore", message="All-NaN")

t0 = time.time()
VOX = 0.01728; DX, DY = -3, -1
Z_STRIDE = 16                  # ~20 planes; the audit used 2
RMAX_SCAN = 1360.0             # level-1 voxels
rng = np.random.default_rng(71)

# CT levels from the zarr root (keys "0" fine, "1" coarse)
L1, L0 = ct_root["1"], ct_root["0"]
SCALE = 2.0                    # level-0 voxels per level-1 voxel
MIN_PITCH = 2.5                # minimum peak distance, level-1 voxels (~43 um)
SMOOTH = 1.0                   # smoothing window, level-1 voxels
NOISE_K = 5.0                  # peak prominence >= NOISE_K * noise sigma (floor 10)

# origins in CT frame (offset applied), same as the audit
if "origins_ct" in dir():
    origins = origins_ct
else:
    from pherc1218_io import load_origins
    origins = load_origins(zs, toward_ct=True)

kmax = max(int(r["k"]) for r in rows)
nzp = len(zs)
Rg = np.full((kmax + 1, 60, nzp), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]), int(round(float(r["theta_deg"]) / 6)) % 60,
       zpos[int(r["z"])]] = float(r["r_l1_vox"])


def ray_profile(arr, zv, ox, oy, a, rr, scale):
    """brightness along one ray. rr in level-1 voxels; arr at `scale`."""
    xs = (ox + rr * np.cos(a)) * scale
    ys = (oy + rr * np.sin(a)) * scale
    x0, x1 = int(xs.min()) - 2, int(xs.max()) + 3
    y0, y1 = int(ys.min()) - 2, int(ys.max()) + 3
    x0, y0 = max(x0, 0), max(y0, 0)
    z = int(round(zv * scale))
    img = np.asarray(arr[z, y0:y1, x0:x1])
    px = np.clip(xs.astype(int) - x0, 0, img.shape[1] - 1)
    py = np.clip(ys.astype(int) - y0, 0, img.shape[0] - 1)
    return img[py, px].astype(np.float32)


# ---------- material threshold per level (same rule as the audit: p5 on known sheets)
def material_threshold(arr, scale):
    mues = []
    for iz in list(range(0, nzp, max(1, nzp // 10)))[:10]:
        zv = zs[iz]; ox, oy = origins[zv]
        kk, ii = np.nonzero(np.isfinite(Rg[:, :, iz]))
        if len(kk) > 300:
            s = rng.choice(len(kk), 300, replace=False); kk, ii = kk[s], ii[s]
        for k_, i_ in zip(kk, ii):
            rr = np.array([Rg[k_, i_, iz]])
            mues.append(ray_profile(arr, zv, ox, oy, np.radians(i_ * 6.0), rr, scale)[0])
    return float(np.percentile(mues, 5))

UMB1 = material_threshold(L1, 1.0)
UMB0 = material_threshold(L0, SCALE)
print(f"material threshold  level1 {UMB1:.0f}   level0 {UMB0:.0f}   [{time.time()-t0:.0f}s]")


def count_column(rr_l, prof, rs, umb, step):
    """the audit's counter. `step` = level-1 voxels per sample (1.0 coarse,
    0.5 fine): smoothing, peak distance and edge windows are scaled so that
    they mean the same physical length at both levels."""
    n3 = max(1, int(round(SMOOTH / step)))
    n7 = max(7, int(round(7 / step)))
    mat = prof >= umb
    suave = np.convolve(prof, np.ones(n3) / n3, mode="same")
    # noise-scaled prominence: sigma from consecutive differences on the
    # labelled stretch (robust MAD), floor 10 as in the audit
    lab = (rr_l >= rs[0]) & (rr_l <= rs[-1])
    d = np.diff(prof[lab]) if lab.sum() > 8 else np.diff(prof)
    sigma = 1.4826 * np.median(np.abs(d - np.median(d))) / np.sqrt(2)
    prom = max(10.0, NOISE_K * sigma / np.sqrt(n3))   # sigma after smoothing
    pk, _ = find_peaks(suave, height=umb,
                       distance=max(1, int(round(MIN_PITCH / step))),
                       prominence=prom)
    rpk = rr_l[pk]
    et0, et1 = rs[0] - 3, rs[-1] + 3
    n_et = int(((rpk >= et0) & (rpk <= et1)).sum())
    eta = n_et / len(rs)
    if not (0.2 <= eta <= 1.5):
        return None
    conv = np.convolve(mat.astype(int), np.ones(n7), mode="same")
    dens = np.flatnonzero(conv >= 4 / step)
    if not len(dens):
        return None
    R_edge = rr_l[dens[-1]]
    w0, w1 = rs[-1] + 6, R_edge
    out = dict(eta=eta, exp=np.nan, det=np.nan, wlen=max(0.0, w1 - w0),
               lab_rho=n_et / eta / len(rs))
    if w1 - w0 >= 20:
        pasos = np.diff(rs[-8:]) if len(rs) >= 8 else np.diff(rs)
        pitch = float(np.median(pasos)) if len(pasos) else 11.6
        pitch = min(max(pitch, 7.0), 25.0)
        out["exp"] = (w1 - w0) / pitch
        out["det"] = ((rpk >= w0) & (rpk <= w1)).sum() / eta
    return out


# ---------- main pass: same columns, two levels ------------------------------
cols = []
z_idx = list(range(0, nzp, Z_STRIDE))
print(f"columns on {len(z_idx)} planes, two levels each ...")
for c_, iz in enumerate(z_idx):
    zv = zs[iz]; ox, oy = origins[zv]
    col_fin = np.isfinite(Rg[:, :, iz])
    for i in range(60):
        ks = np.flatnonzero(col_fin[:, i])
        if len(ks) < 8:
            continue
        rs = np.sort(Rg[ks, i, iz]); a = np.radians(i * 6.0)
        r_start = max(0.0, rs[0] - 10)
        rr1 = np.arange(r_start, RMAX_SCAN, 1.0)
        rr0 = np.arange(r_start, RMAX_SCAN, 1.0 / SCALE)
        try:
            p1 = ray_profile(L1, zv, ox, oy, a, rr1, 1.0)
            p0 = ray_profile(L0, zv, ox, oy, a, rr0, SCALE)
        except Exception as e:      # box outside the volume etc.
            continue
        c1 = count_column(rr1, p1, rs, UMB1, 1.0)
        c0 = count_column(rr0, p0, rs, UMB0, 1.0 / SCALE)
        if c1 is None or c0 is None:
            continue
        cols.append(dict(i=i, iz=iz, eta1=c1["eta"], eta0=c0["eta"],
                         exp1=c1["exp"], det1=c1["det"],
                         exp0=c0["exp"], det0=c0["det"],
                         lab1=c1["lab_rho"], lab0=c0["lab_rho"]))
    print(f"  plane {c_+1}/{len(z_idx)}  columns so far {len(cols)}  [{time.time()-t0:.0f}s]")

if len(cols) < 30:
    raise SystemExit(f"only {len(cols)} usable columns: not enough to read the exam")

eta1 = np.array([c["eta1"] for c in cols]); eta0 = np.array([c["eta0"] for c in cols])
exp1 = np.array([c["exp1"] for c in cols]); det1 = np.array([c["det1"] for c in cols])
exp0 = np.array([c["exp0"] for c in cols]); det0 = np.array([c["det0"] for c in cols])

# ---------- E1 -----------------------------------------------------------------
med_eta0 = float(np.median(eta0)); med_d = float(np.median(np.abs(eta0 - eta1)))
e1 = (0.3 <= med_eta0 <= 1.2) and (med_d <= 0.25)
print(f"\nEXAM E1 - counter at the fine level on known sheets: "
      f"median eta0 {med_eta0:.2f} (eta1 {np.median(eta1):.2f}), "
      f"median |eta0-eta1| {med_d:.2f}  -> {'PASS' if e1 else 'FAIL'}")
if not e1:
    print("E1 failed: the fine count is not trustworthy; E2 is not read. STOP.")
    raise SystemExit(1)

# ---------- E2 -----------------------------------------------------------------
q = np.isfinite(exp1) & np.isfinite(exp0) & (exp1 >= 3)
n = int(q.sum())
if n < 20:
    raise SystemExit(f"only {n} wedge columns with >= 3 expected sheets: E2 cannot be read")
rho1 = det1[q].sum() / exp1[q].sum()
rho0 = det0[q].sum() / exp0[q].sum()
D = rho0 - rho1
boots = []
idx = np.flatnonzero(q)
for _ in range(2000):
    s = rng.choice(idx, len(idx), replace=True)
    boots.append(det0[s].sum() / exp0[s].sum() - det1[s].sum() / exp1[s].sum())
lo, hi = np.percentile(boots, [2.5, 97.5])
if rho1 >= 0.60:
    v2a = "LAMINATED - the sheets are there; the audit's 0.34 was the counter floor"
elif rho1 <= 0.25:
    v2a = "FUSED - confirmed with a counter that can see 43 um"
else:
    v2a = "UNDECIDED"
if D >= 0.25 and lo > 0:
    v2b = "YES - the fine level shows more sheets: resolution mattered"
elif D < 0.10:
    v2b = "NO - level 1 suffices; finer voxels add nothing"
else:
    v2b = "UNDECIDED"
verdict = f"E2a {v2a} | E2b {v2b}"
print(f"EXAM E2 - wedge columns with >= 3 expected sheets: n = {n}")
print(f"  rho level1 = {rho1:.2f}  (audit, 100 um floor: 0.34)")
print(f"  rho level0 = {rho0:.2f}   D = {D:+.2f}  [CI95 {lo:+.2f}, {hi:+.2f}]")
print(f"VERDICT E2a (main): {v2a}")
print(f"VERDICT E2b (fine level): {v2b}")
print(f"CONTROL C - labelled stretch: median count/known  level1 "
      f"{np.median([c['lab1'] for c in cols]):.2f}   level0 "
      f"{np.median([c['lab0'] for c in cols]):.2f}   (~1 expected)")

np.savez("cunas_fino_1218.npz", eta1=eta1, eta0=eta0, exp1=exp1, det1=det1,
         exp0=exp0, det0=det0, i=[c["i"] for c in cols], iz=[c["iz"] for c in cols],
         rho1=rho1, rho0=rho0, D=D, ci=[lo, hi], verdict=verdict)

fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
ax[0].scatter(eta1, eta0, s=8, alpha=.5); ax[0].plot([0, 1.5], [0, 1.5], "g--")
ax[0].set_xlabel("counter efficiency, level 1"); ax[0].set_ylabel("level 0")
ax[0].set_title("E1: known sheets, both levels")
ax[1].scatter(det1[q] / exp1[q], det0[q] / exp0[q], s=8, alpha=.5)
ax[1].plot([0, 1.5], [0, 1.5], "g--"); ax[1].set_xlim(0, 1.5); ax[1].set_ylim(0, 1.5)
ax[1].set_xlabel("rho per column, level 1 (17 um)")
ax[1].set_ylabel("rho per column, level 0 (8.6 um)")
ax[1].set_title(f"E2: wedges  rho {rho1:.2f} -> {rho0:.2f}  D {D:+.2f}")
plt.tight_layout(); plt.savefig("cunas_fino_1218.png", dpi=130)
print(f"saved cunas_fino_1218.npz / .png   [{time.time()-t0:.0f}s]")

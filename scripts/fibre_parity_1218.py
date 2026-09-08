#!/usr/bin/env python3
"""
fibre_parity_1218.py — DOES A PAPYRUS SHEET CARRY ITS OWN MARKER AT 8.6 um?

HYPOTHESIS (plain words). A papyrus sheet is two layers of crossed strips:
one running along the roll (horizontal, the written recto) and one running
up-down (vertical, the verso). In a roll every sheet faces the same way, so
walking outward through a stack of sheets the fibre direction alternates
horizontal, vertical, horizontal, vertical... Each flip = one sheet, whether
or not there is a gap between sheets. Two facts point at this: at 17 um the
sheets show no texture at all (mode 15 re-run, 7 Sep) but at 8.6 um a known
sheet gives MORE ridges than one (wedge_fine_1218, 6 Sep). If the flip is
visible at 8.6 um on KNOWN sheets, it is a way to count sheets in fused
stacks that does not depend on gaps, brightness or the 60-ray geometry.

WHAT IS MEASURED. For a sample of known crossings (z, theta, k) a small 3-D
box of CT level 0 is read around the crossing. Along the ray, in steps of one
fine voxel, a flat patch of the sheet (tangential x height) is taken; after
removing a fitted plane (a tilted sheet would otherwise fake a direction)
the gradient energies along the two axes give an anisotropy
    a = (E_t - E_z) / (E_t + E_z)
    a < 0 : intensity varies less along t than along z -> fibres run along t
            (HORIZONTAL, roll direction)
    a > 0 : fibres run along z (VERTICAL)
Sheet thickness comes for free: the material run along the ray.

PRE-REGISTERED EXAM (thresholds fixed before the run):
  E1  signal exists: median |a| inside the sheet core (central 60 % of the
      material run) must exceed the 95th percentile of |a| from the same
      patches with pixels shuffled. Else STOP.
  E2  the marker: per sheet, a_in (inner half of the core) and a_out (outer
      half). FLIP if signs differ and both |a| > a_min = null p95.
        flips in >= 70 % of sheets AND the same order (which half is
        horizontal) in >= 80 % of the flipping sheets -> MARKER EXISTS
        flips < 50 %, or order < 60 %                  -> NO MARKER
        otherwise                                      -> UNDECIDED
      Chance level: ~50 % flips, ~50 % order.
  C   control: the same statistic on a patch of AIR 6 fine voxels outside
      the sheet (must not flip consistently) — reported, not a gate.
  REPORT thickness in um: median, inner third vs outer third of the roll.
  ONE RUN. Nothing is tuned after seeing the numbers.
  TWIN (fibre_parity_twin_1218.py, neighbour-bounded version): layers MARKER
      100 % / tilted 15 deg MARKER 91 % / FUSED sheets (no air) MARKER 100 % /
      smooth E1 FAIL / uniform (one direction) NO MARKER 0 %.

SHEET EXTENT (changed 7 Sep after a diagnostic run, before any exam was read):
delimiting a sheet by its brightness valleys fails on PHerc. 1218 — in 99 of
120 sampled sheets the material runs unbroken for more than 250 um at half
peak (sheets are pressed together; only ~1 in 10 is isolated). The sheet is
therefore bounded by its neighbours' crossings on the same ray: the core is
the central 60 % of the interval between the two midpoints, intersected with
material. The air control is the midpoint to the next sheet outward (the
valley, seen or not). The exam thresholds are unchanged.

INPUTS. rows, zs, zpos, origins_ct (pherc1218_io), ct_root["0"].
OUTPUT. fibre_parity_1218.npz, fibre_parity_1218.png.
COST. N_SAMPLES small boxes of level 0; ~10-20 min on Colab.
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

import numpy as np, matplotlib.pyplot as plt, time, warnings
from scipy.ndimage import map_coordinates
warnings.filterwarnings("ignore")

t0 = time.time()
VOX = 0.01728; FINE = VOX / 2          # mm per level-0 voxel (8.64 um)
SCALE = 2.0
N_SAMPLES = 300                        # known crossings examined
HALF_R = 18                            # fine voxels each side along the ray (~155 um)
HALF_T = 10                            # patch half-size, tangential (~85 um)
HALF_Z = 8                             # patch half-size, height (~70 um)
MAT_FRAC = 0.5                         # material = above this fraction of the sheet peak
N_SHUF = 20                            # shuffles per patch for the null
rng = np.random.default_rng(1218)
L0 = ct_root["0"]

# ---- sample of known crossings: spread over planes, rays and depth ----------
kmax = max(int(r["k"]) for r in rows)
arr = np.array([(int(r["z"]), float(r["theta_deg"]), int(r["k"]), float(r["r_l1_vox"]))
                for r in rows])
# depth thirds by k, one third of the sample each; avoid the two innermost k
thirds = [(2, kmax // 3), (kmax // 3, 2 * kmax // 3), (2 * kmax // 3, kmax)]
picked = []
for lo, hi in thirds:
    pool = np.flatnonzero((arr[:, 2] >= lo) & (arr[:, 2] < hi))
    picked.extend(rng.choice(pool, N_SAMPLES // 3, replace=False))
sample = arr[np.array(picked)]
rk = {(int(z), round(th, 1), int(k)): r for z, th, k, r in arr}   # (z, theta, k) -> r
print(f"{len(sample)} known crossings sampled over {len(set(sample[:,0]))} planes "
      f"and k {int(sample[:,2].min())}..{int(sample[:,2].max())}")


def read_box(z, cx, cy, r, theta):
    """3-D box of level 0 around the crossing, resampled into (d, t, zz)
    coordinates: d along the ray (out = +), t tangential, zz height.
    Two passes: the first finds the sheet's local tilt (position of its
    brightness peak across the patch, fitted by a plane); the second
    resamples with that tilt removed, so the sheet lies flat in the box.
    Returns (box, (raw, resample)); resample(raw2) applies the same final
    rotation+shear to another raw array of the same shape (for the null)."""
    a = np.radians(theta)
    d = np.arange(-HALF_R, HALF_R + 1)
    t = np.arange(-HALF_T, HALF_T + 1)
    zz = np.arange(-HALF_Z, HALF_Z + 1)
    D, T, Z = np.meshgrid(d, t, zz, indexing="ij")

    def coords(shear):
        Dd = D + shear
        X = (cx + r * np.cos(a)) * SCALE + Dd * np.cos(a) - T * np.sin(a)
        Y = (cy + r * np.sin(a)) * SCALE + Dd * np.sin(a) + T * np.cos(a)
        return X, Y, z * SCALE + Z

    X, Y, Zf = coords(0.0)
    m = max(HALF_T, HALF_Z) + 2          # margin for the shear of pass 2
    x0, x1 = int(X.min()) - m, int(X.max()) + m + 1
    y0, y1 = int(Y.min()) - m, int(Y.max()) + m + 1
    z0, z1 = int(Zf.min()) - 1, int(Zf.max()) + 2
    if min(x0, y0, z0) < 0:
        return None, None
    sub = np.asarray(L0[z0:z1, y0:y1, x0:x1]).astype(np.float32)
    if sub.size == 0 or sub.shape[0] < 3:
        return None, None
    box0 = map_coordinates(sub, [Zf - z0, Y - y0, X - x0], order=1, mode="nearest")
    # pass 1: where is the sheet's peak in each (t, zz) column, near d = 0?
    w = slice(HALF_R - 6, HALF_R + 7)
    pk = np.argmax(box0[w], axis=0) - 6                     # (t, zz) in fine voxels
    A = np.c_[T[0].ravel(), Z[0].ravel(), np.ones(T[0].size)]
    coef, *_ = np.linalg.lstsq(A, pk.ravel().astype(float), rcond=None)
    shear = (A @ coef).reshape(T[0].shape)[None] - coef[2]  # plane without offset
    if abs(coef[0]) > 1.0 or abs(coef[1]) > 1.0:            # > 45 deg: not a sheet
        return None, None
    X, Y, Zf = coords(shear)
    cc = [Zf - z0, Y - y0, X - x0]
    resample = lambda raw: map_coordinates(raw, cc, order=1, mode="nearest")
    return resample(sub), (sub, resample)


def anisotropy(patch):
    """patch (t, z): remove a fitted plane, then a = (E_t - E_z)/(E_t + E_z)."""
    T, Z = np.meshgrid(np.arange(patch.shape[0]), np.arange(patch.shape[1]), indexing="ij")
    A = np.c_[T.ravel(), Z.ravel(), np.ones(T.size)]
    coef, *_ = np.linalg.lstsq(A, patch.ravel(), rcond=None)
    p = patch - (A @ coef).reshape(patch.shape)
    gt = np.diff(p, axis=0); gz = np.diff(p, axis=1)
    et, ez = float(np.mean(gt ** 2)), float(np.mean(gz ** 2))
    return (et - ez) / (et + ez + 1e-9)


recs = []
for n, (z, th, k, r) in enumerate(sample):
    cx, cy = origins_ct[int(z)]
    box, raw = read_box(int(z), cx, cy, r, th)
    if box is None:
        continue
    c_t, c_z = HALF_T, HALF_Z
    prof = box[:, c_t-2:c_t+3, c_z-2:c_z+3].mean(axis=(1, 2))   # centre line along the ray
    peak = prof.max()
    mat = prof >= MAT_FRAC * peak
    i0 = HALF_R
    if not mat[i0]:
        continue
    # sheet extent from the neighbours on the same ray (fine voxels)
    key = (int(z), round(th, 1), int(k))
    r_m = rk.get((key[0], key[1], key[2] - 1)); r_p = rk.get((key[0], key[1], key[2] + 1))
    if r_m is None or r_p is None:
        continue
    dm = (r - r_m) * SCALE / 2; dp = (r_p - r) * SCALE / 2      # to the midpoints
    if dm < 3 or dp < 3 or dp > HALF_R - 1:
        continue
    idx = np.arange(len(prof)) - i0
    core = np.flatnonzero((idx >= -0.6 * dm) & (idx <= 0.6 * dp) & mat)
    if len(core) < 5:
        continue
    # thickness at half peak, only if a valley exists within the interval
    lo = i0
    while lo > 0 and mat[lo - 1]:
        lo -= 1
    hi = i0
    while hi < len(mat) - 1 and mat[hi + 1]:
        hi += 1
    run = hi - lo + 1
    isolated = (lo > 0 and hi < len(mat) - 1)
    a_d = np.array([anisotropy(box[i]) for i in core])
    # null: the RAW box with its voxels shuffled, then the same rotation and
    # the same patches -> carries the interpolation bias of the data
    sub, resample = raw
    a_null = []
    flat = sub.ravel().copy()
    for _ in range(N_SHUF):
        rng.shuffle(flat)
        nb = resample(flat.reshape(sub.shape))
        a_null.extend(anisotropy(nb[i]) for i in core[:: max(1, len(core) // 3)])
    a_null = np.array(a_null)
    bias = float(np.median(a_null))                  # interpolation bias, removed
    a_d = a_d - bias
    half = len(core) // 2
    a_in, a_out = float(np.median(a_d[:half])), float(np.median(a_d[half:]))
    # air control: the midpoint to the next sheet outward (the valley)
    j = i0 + int(round(dp))
    a_air = anisotropy(box[j]) - bias if j < box.shape[0] else np.nan
    recs.append(dict(z=z, th=th, k=k, run_um=run * FINE * 1000 if isolated else np.nan,
                     pitch_um=(dm + dp) * FINE * 1000,
                     a_in=a_in, a_out=a_out, a_core=float(np.median(np.abs(a_d))),
                     null=np.abs(a_null - bias), a_air=a_air))
    if n % 50 == 0:
        print(f"  {n}/{len(sample)}  usable {len(recs)}  [{time.time()-t0:.0f}s]")

if len(recs) < 60:
    raise SystemExit(f"only {len(recs)} usable sheets: exam not readable")
print(f"usable sheets: {len(recs)}  [{time.time()-t0:.0f}s]")

core = np.array([r["a_core"] for r in recs])
null95 = float(np.percentile(np.concatenate([r["null"] for r in recs]), 95))
e1 = float(np.median(core)) > null95
print(f"\nEXAM E1 - fibre direction visible: median |a| in sheet core "
      f"{np.median(core):.3f} vs null p95 {null95:.3f} -> {'PASS' if e1 else 'FAIL'}")
if not e1:
    print("No direction signal at 8.6 um on known sheets. STOP; E2 not read.")
    raise SystemExit(1)

a_in = np.array([r["a_in"] for r in recs]); a_out = np.array([r["a_out"] for r in recs])
strong = (np.abs(a_in) > null95) & (np.abs(a_out) > null95)
flip = strong & (np.sign(a_in) != np.sign(a_out))
f_flip = flip.mean()
order = (a_in[flip] < 0).mean() if flip.any() else np.nan   # inner horizontal?
f_order = max(order, 1 - order) if flip.any() else np.nan
if f_flip >= 0.70 and f_order >= 0.80:
    v = "MARKER EXISTS - one direction flip per sheet, same order in the roll"
elif f_flip < 0.50 or f_order < 0.60:
    v = "NO MARKER - flips at chance level or in no consistent order"
else:
    v = "UNDECIDED"
which = "inner half HORIZONTAL (recto in)" if order >= 0.5 else "inner half VERTICAL"
print(f"EXAM E2 - flips in {f_flip:.0%} of sheets ({flip.sum()}/{len(recs)}), "
      f"same order in {f_order:.0%} of flipping sheets [{which}]")
print(f"VERDICT: {v}")
a_air = np.array([r["a_air"] for r in recs]); a_air = a_air[np.isfinite(a_air)]
print(f"CONTROL C - air outside the sheet: median |a| {np.median(np.abs(a_air)):.3f} "
      f"(null p95 {null95:.3f}); sign +{np.mean(a_air>0):.0%}/-{np.mean(a_air<0):.0%}")
th_um = np.array([r["run_um"] for r in recs]); kk = np.array([r["k"] for r in recs])
iso = np.isfinite(th_um)
pitch = np.array([r["pitch_um"] for r in recs])
print(f"THICKNESS - isolated sheets (a valley on both sides): {iso.sum()}/{len(recs)}; "
      f"their run at half peak: median {np.median(th_um[iso]) if iso.any() else float('nan'):.0f} um; "
      f"local pitch median {np.median(pitch):.0f} um "
      f"(inner third {np.median(pitch[kk < kmax//3]):.0f}, outer third {np.median(pitch[kk >= 2*kmax//3]):.0f})")

np.savez("fibre_parity_1218.npz", a_in=a_in, a_out=a_out, core=core, null95=null95,
         run_um=th_um, k=kk, z=[r["z"] for r in recs], th=[r["th"] for r in recs],
         a_air=a_air, f_flip=f_flip, f_order=f_order, verdict=v)
fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
ax[0].scatter(a_in, a_out, s=10, alpha=.6, c=np.where(flip, "tab:green", "gray"))
ax[0].axhline(0, color="k", lw=.5); ax[0].axvline(0, color="k", lw=.5)
ax[0].set_xlabel("a, inner half of sheet"); ax[0].set_ylabel("a, outer half")
ax[0].set_title(f"E2: flips {f_flip:.0%}, order {f_order:.0%}")
ax[1].hist(pitch, bins=30); ax[1].set_xlabel("local pitch between sheets (um)")
ax[1].set_title(f"median {np.median(pitch):.0f} um")
plt.tight_layout(); plt.savefig("fibre_parity_1218.png", dpi=130)
print(f"saved fibre_parity_1218.npz / .png  [{time.time()-t0:.0f}s]")

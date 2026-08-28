#!/usr/bin/env python3
"""
recovery_probe_1218.py — the RECOVERY MAP: what does the raw CT hold where the
absent windings should pass?

Idea: the census gaps are not the end - the position of an absent winding is
predicted from its neighbours (PL-4: 32-60 um) and the raw CT says whether
there is unlabelled material there (RECOVERABLE) or void (LOST). A companion
check had already ruled out the other route: the neighbours did not swallow the
absent windings (5.4%, and no excess thickness).

METHOD, with the control built in:
 - r_hat for each gap by interpolation in k over the windings present at the
   same (theta, z); the distance to the nearest measured winding (dk) is kept:
   dk=1 validated at 32 um, dk=2 at 60 um (PL-4); dk <= 3
 - CONTROL: in each plane, positions of PRESENT windings are sampled the same
   way (max over r +/- 2), so the "there is material" distribution is
   calibrated against itself; the threshold is the control's 5th percentile,
   PRINTED BEFORE IT IS APPLIED
 - VERDICT per gap: RECOVERABLE (>= threshold) / LOST (< threshold)

INPUTS (this was run as a Colab cell): expects `vol` already in namespace - the
memory-mapped raw CT volume from the texture-setup step. Does NOT need the
crossing-table loading step; it reads the winding maps and origins from the
labels' author's repository over HTTP. ~12 min at Z_STRIDE=2.

OUTPUTS: recuperable_1218.npz, mapa_recuperable_1218.png
"""
import numpy as np, matplotlib.pyplot as plt, csv, io, urllib.request
import warnings, time
warnings.filterwarnings("ignore", message="All-NaN")

t0 = time.time()
assert "vol" in dir(), "falta vol: corre TEX-0 primero"
VOX = 0.01728; DX, DY = -3, -1
Z_STRIDE = 2; DK_MAX = 3
RAWJ = ("https://raw.githubusercontent.com/Jinhojeong/"
        "vesuvius-surface-geometry-diagnostic/main/results/kollesis/")

# mapas de J (Ruta A) y origenes
datos = urllib.request.urlopen(RAWJ + "route_a/winding_maps_1218.npz").read()
mj = np.load(io.BytesIO(datos))
n, p10, p90, zs_arr = mj["n"], mj["r_p10"], mj["r_p90"], mj["zs"]
nk, _, nzp = n.shape
ok = n >= 20
rmid = np.where(ok, (p90 + p10) / 2, np.nan)
texto = urllib.request.urlopen(RAWJ + "origins_merged.csv").read().decode()
acum = {}
for f_ in csv.DictReader(io.StringIO(texto)):
    z = int(float(f_["z"]))
    acum.setdefault(z, []).append((float(f_["cx"]), float(f_["cy"])))
origins = {z: (np.mean([p[0] for p in v]) + DX,
               np.mean([p[1] for p in v]) + DY) for z, v in acum.items()}
zso = sorted(origins)
for z in zs_arr:
    z = int(z)
    if z not in origins:
        origins[z] = origins[min(zso, key=lambda q: abs(q - z))]

# r_hat de huecos por interpolacion en k (por columna theta,z), con dk al vecino
K0, K1 = 2, 79
R_hat = np.full((nk, 60, nzp), np.nan, np.float32)
DKn   = np.full((nk, 60, nzp), 99, np.int8)
for i in range(60):
    for iz in range(nzp):
        col = rmid[:, i, iz]
        kk = np.flatnonzero(np.isfinite(col))
        if len(kk) < 2: continue
        falta = np.array([k for k in range(K0, K1 + 1)
                          if not np.isfinite(col[k])])
        if not len(falta): continue
        dentro = falta[(falta > kk[0]) & (falta < kk[-1])]
        if not len(dentro): continue
        R_hat[dentro, i, iz] = np.interp(dentro, kk, col[kk])
        idx = np.searchsorted(kk, dentro)
        dk = np.minimum(dentro - kk[idx - 1], kk[idx] - dentro)
        DKn[dentro, i, iz] = np.clip(dk, 0, 99)
cand = np.isfinite(R_hat) & (DKn <= DK_MAX)
print(f"posiciones de vuelta ausente con r_hat fiable (dk<={DK_MAX}): "
      f"{cand.sum():,}  [{time.time()-t0:.0f}s]")

# muestreo del CT: huecos + control (vueltas presentes)
BH = np.full((nk, 60, nzp), np.nan, np.float32)   # brillo en huecos
ctrl = []
z_idx = list(range(0, nzp, Z_STRIDE))
print(f"muestreando {len(z_idx)} planos...")
for c_, iz in enumerate(z_idx):
    zv = int(zs_arr[iz])
    ox, oy = origins[zv]
    kk_h, ii_h = np.nonzero(cand[:, :, iz])
    kk_c, ii_c = np.nonzero(ok[:, :, iz])
    if len(kk_c) > 400:                       # control: submuestra por plano
        sel = np.random.default_rng(iz).choice(len(kk_c), 400, replace=False)
        kk_c, ii_c = kk_c[sel], ii_c[sel]
    rr = np.concatenate([R_hat[kk_h, ii_h, iz], rmid[kk_c, ii_c, iz]])
    aa = np.radians(np.concatenate([ii_h, ii_c]) * 6.0)
    if not len(rr): continue
    xs = ox + rr * np.cos(aa); ys = oy + rr * np.sin(aa)
    x0 = max(0, int(xs.min()) - 5); x1 = int(xs.max()) + 6
    y0 = max(0, int(ys.min()) - 5); y1 = int(ys.max()) + 6
    img = np.asarray(vol[zv, y0:y1, x0:x1])
    rmat = rr[:, None] + np.arange(-2, 3)[None, :]
    px = np.clip(np.round(ox + rmat * np.cos(aa)[:, None]).astype(int) - x0,
                 0, img.shape[1] - 1)
    py = np.clip(np.round(oy + rmat * np.sin(aa)[:, None]).astype(int) - y0,
                 0, img.shape[0] - 1)
    val = img[py, px].max(axis=1).astype(np.float32)
    BH[kk_h, ii_h, iz] = val[:len(kk_h)]
    ctrl.append(val[len(kk_h):])
    if c_ % 30 == 0:
        print(f"  {c_}/{len(z_idx)}  [{time.time()-t0:.0f}s]")
ctrl = np.concatenate(ctrl)

# umbral desde el CONTROL (impreso antes de aplicar)
print(f"\nCONTROL (vueltas presentes, n={len(ctrl):,}): "
      f"p5 {np.percentile(ctrl,5):.0f}  p25 {np.percentile(ctrl,25):.0f}  "
      f"p50 {np.percentile(ctrl,50):.0f}")
hb = BH[np.isfinite(BH)]
print(f"HUECOS (n={len(hb):,}): p25 {np.percentile(hb,25):.0f}  "
      f"p50 {np.percentile(hb,50):.0f}  p75 {np.percentile(hb,75):.0f}")
UMBRAL = np.percentile(ctrl, 5)
rec = np.isfinite(BH) & (BH >= UMBRAL)
per = np.isfinite(BH) & (BH < UMBRAL)
fr = rec.sum() / max(1, rec.sum() + per.sum())
print(f"\numbral (p5 del control) = {UMBRAL:.0f}")
print(f"RECUPERABLE (material sin etiquetar): {rec.sum():,} ({fr:.1%})")
print(f"PERDIDO (vacio): {per.sum():,} ({1-fr:.1%})")
for dk in (1, 2, 3):
    q = np.isfinite(BH) & (DKn == dk)
    if q.sum():
        fq = (q & rec).sum() / q.sum()
        print(f"  dk={dk}: {q.sum():,} posiciones, recuperable {fq:.1%}")

# mapa (L,z): reutiliza la geometria mediana para el eje L
rk_ray = np.nanmedian(rmid, axis=2) * VOX
rk = np.nanmedian(rk_ray, axis=1)
f2 = np.isfinite(rk); ks = np.arange(nk)
rk = np.interp(ks, ks[f2], rk[f2])
for k in range(nk):
    fila = rk_ray[k]; fila[~np.isfinite(fila)] = rk[k]
rv = rk_ray.ravel()
seg = np.sqrt((rv*np.radians(6))**2 + np.diff(rv, prepend=rv[0])**2)
Lfin = np.cumsum(seg)
M = np.full((nk*60, nzp), np.nan, np.float32)
M[rec.reshape(nk*60, nzp)] = 1.0
M[per.reshape(nk*60, nzp)] = 0.0
dom = Lfin < 5200
plt.figure(figsize=(16, 4.5))
plt.pcolormesh(np.r_[0, Lfin[dom]]/1000, np.arange(nzp+1),
               M[dom].T, cmap="RdYlGn", vmin=0, vmax=1)
plt.colorbar(label="1 = material sin etiquetar (recuperable) / 0 = vacio",
             pad=0.01)
plt.xlabel("L desarrollada (m)"); plt.ylabel("plano z")
plt.title(f"MAPA DE RECUPERABILIDAD - vueltas ausentes con r_hat fiable: "
          f"{fr:.0%} tiene material esperando etiqueta")
plt.tight_layout()
plt.savefig("mapa_recuperable_1218.png", dpi=140, bbox_inches="tight")
np.savez_compressed("recuperable_1218.npz", brillo=BH, r_hat=R_hat,
                    dk=DKn, umbral=UMBRAL, zs=zs_arr)
print(f"\nficheros escritos  [{time.time()-t0:.0f}s]")

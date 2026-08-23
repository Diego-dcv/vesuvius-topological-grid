
import numpy as np, matplotlib.pyplot as plt, csv, io, urllib.request
import warnings
warnings.filterwarnings("ignore", message="All-NaN")

for v in ["rows", "zs", "zpos", "dz_mm", "vol"]:
    assert v in dir(), f"falta {v}: corre carga de tabla y TEX-0"
VOX = 0.01728; COB_MIN = 0.10; MATU = 50
DX, DY = -3, -1
Z_STRIDE = 2
RAW = ("https://raw.githubusercontent.com/Jinhojeong/"
       "vesuvius-surface-geometry-diagnostic/main/results/kollesis/")

# orígenes
texto = urllib.request.urlopen(RAW + "origins_merged.csv").read().decode()
acum = {}
for f_ in csv.DictReader(io.StringIO(texto)):
    z = int(float(f_["z"]))
    acum.setdefault(z, []).append((float(f_["cx"]), float(f_["cy"])))
origins = {z: (np.mean([p[0] for p in v]) + DX,
               np.mean([p[1] for p in v]) + DY) for z, v in acum.items()}
zso = sorted(origins)
for z in zs:
    if z not in origins:
        origins[z] = origins[min(zso, key=lambda q: abs(q - z))]

# geometría L (la de DES-1)
kmax = max(int(r["k"]) for r in rows)
nz = len(zs)
Rg = np.full((kmax + 1, 60, nz), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]),
       int(round(float(r["theta_deg"]) / 6)) % 60,
       zpos[int(r["z"])]] = float(r["r_l1_vox"]) * VOX
cob = np.isfinite(Rg).reshape(kmax + 1, -1).mean(axis=1)
K0 = 2
K1 = max(k for k in range(kmax + 1) if cob[k] >= COB_MIN)
nk = K1 - K0 + 1
rmed = np.nanmedian(Rg[K0:K1 + 1], axis=2)
rk = np.nanmedian(rmed, axis=1)
f = np.isfinite(rk)
rk = np.interp(np.arange(nk), np.arange(nk)[f], rk[f])
for a in range(nk):
    fila = rmed[a]; fila[~np.isfinite(fila)] = rk[a]
rv = rmed.ravel()
seg = np.sqrt((rv * np.radians(6.0)) ** 2
              + np.diff(rv, prepend=rv[0]) ** 2)
Lfin = np.cumsum(seg); Lc = Lfin - seg / 2
zs_arr = np.array(sorted(zs))

# agrupar cruces por rebanada
por_z = {}
for r in rows:
    k = int(r["k"])
    if not (K0 <= k <= K1):
        continue
    por_z.setdefault(int(r["z"]), []).append(
        (k, int(round(float(r["theta_deg"]) / 6)) % 60,
         float(r["r_l1_vox"])))

# muestrear el CT rebanada a rebanada y pintar en (L, z)
nbL = int(Lfin[-1] / 2.0)                 # bins de 2 mm en L
SUM = np.zeros((nbL, nz), np.float32)
CNT = np.zeros((nbL, nz), np.float32)
en_mat = 0; tot = 0
z_list = sorted(por_z)[::Z_STRIDE]
print(f"muestreando {len(z_list)} rebanadas (Z_STRIDE={Z_STRIDE})...")
for n_, zv in enumerate(z_list):
    pts = por_z[zv]
    ox, oy = origins[zv]
    kk = np.array([p[0] for p in pts]); ib = np.array([p[1] for p in pts])
    rr = np.array([p[2] for p in pts])
    aa = np.radians(ib * 6.0)
    xs = ox + rr * np.cos(aa); ys = oy + rr * np.sin(aa)
    x0 = max(0, int(xs.min()) - 5); x1 = int(xs.max()) + 6
    y0 = max(0, int(ys.min()) - 5); y1 = int(ys.max()) + 6
    img = np.asarray(vol[zv, y0:y1, x0:x1])
    rmat = rr[:, None] + np.arange(-2, 3)[None, :]
    px = np.clip(np.round(ox + rmat * np.cos(aa)[:, None]).astype(int)
                 - x0, 0, img.shape[1] - 1)
    py = np.clip(np.round(oy + rmat * np.sin(aa)[:, None]).astype(int)
                 - y0, 0, img.shape[0] - 1)
    val = img[py, px].max(axis=1).astype(np.float32)
    en_mat += int((val > MATU).sum()); tot += len(val)
    Lb = np.clip((Lc[(kk - K0) * 60 + ib] / (Lfin[-1] / nbL)).astype(int),
                 0, nbL - 1)
    iz = zpos[zv]
    np.add.at(SUM, (Lb, iz), val)
    np.add.at(CNT, (Lb, iz), 1)
    if n_ % 40 == 0:
        print(f"  {n_}/{len(z_list)}")
IMG = np.divide(SUM, CNT, out=np.full_like(SUM, np.nan), where=CNT > 0)
print(f"cruces muestreados: {tot:,}; {100*en_mat/tot:.0f}% en material "
      "(sanity: esperable ~90%, coherente con la contención de anclas)")

plt.figure(figsize=(20, 4.5))
v0, v1 = np.nanpercentile(IMG, [2, 98])
plt.imshow(IMG.T, aspect="auto", origin="lower", cmap="gray",
           vmin=v0, vmax=v1, extent=[0, Lfin[-1] / 1000, 0, nz * dz_mm])
plt.colorbar(label="intensidad CT en la hoja", pad=0.01)
plt.xlabel("desarrollo del papiro (m)")
plt.ylabel("altura (mm)")
plt.title("PHerc1218 — la hoja plana TEXTURIZADA: el brillo del CT "
          "llevado al desenrollado (densidad y daño, no letras)")
plt.tight_layout()
plt.savefig("hoja_plana_texturizada_1218.png", dpi=140,
            bbox_inches="tight")
plt.show()
print("guardada hoja_plana_texturizada_1218.png")
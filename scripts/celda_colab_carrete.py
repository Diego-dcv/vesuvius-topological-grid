# =====================================================================
# CELDA "CARRETE" — PHerc1218
# Cuánto papel cabe en el corte del rollo, a 9 alturas.
# Idea: el papel ocupa sitio. Área del corte / separación entre hojas
# = metros de papel. Y con el perímetro exterior, cuántas vueltas.
# No usa etiquetas ni conteos: solo el escáner.
# Autónoma: pegar entera en una celda de Colab y ejecutar. ~5-15 min.
# Guarda carrete_1218.csv y carrete_1218.png en Drive/vesuvius_1218/
# =====================================================================

import subprocess, sys, os, time
try:
    import zarr, s3fs
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "zarr", "s3fs"], check=True)
    import zarr, s3fs
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu
from skimage.measure import find_contours, label

# ---- Drive ----------------------------------------------------------
try:
    from google.colab import drive
    drive.mount("/content/drive")
    OUT = "/content/drive/MyDrive/vesuvius_1218"
except Exception:
    OUT = "./vesuvius_1218"
os.makedirs(OUT, exist_ok=True)

# ---- escáner --------------------------------------------------------
VOLUME = ("vesuvius-challenge-open-data/PHerc1218/volumes/"
          "20250521120456-8.640um-1.2m-116keV-masked.zarr")
root = zarr.open(s3fs.S3Map(VOLUME, s3=s3fs.S3FileSystem(anon=True)), mode="r")
keys = sorted(root.keys())
LVL = 2 if "2" in keys else 1
arr = root[str(LVL)]
PX = 0.00864 * 2**LVL                      # mm por píxel en este nivel
print(f"escáner abierto: nivel {LVL} ({PX*1000:.1f} µm/píxel), forma {arr.shape}")

# 9 alturas repartidas por el cuerpo del rollo (en unidades de la tabla, nivel 1)
Z_L1 = np.linspace(2000, 10000, 9).astype(int)

# separaciones entre hojas a probar (mm). 0,164 = la más favorable a "muchas vueltas"
S_LIST = [0.164, 0.17, 0.18, 0.19]
CORE_PER = (0.0, 26.0)   # perímetro de la vuelta más interna: 0 (máximo de vueltas) a 26 mm


def envelope(img, px_mm, close_mm=0.5):
    nz = img[img > 0]
    thr = threshold_otsu(nz) if nz.size > 100 else 0
    mat = img > thr
    r = max(1, int(round(close_mm / px_mm)))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (xx**2 + yy**2) <= r * r
    p = r + 2
    env = ndi.binary_closing(np.pad(mat, p), structure=disk)[p:-p, p:-p]
    env = ndi.binary_fill_holes(env)
    lab = label(env)
    if lab.max() == 0:
        return None
    sizes = np.bincount(lab.ravel()); sizes[0] = 0
    env = lab == sizes.argmax()
    cs = find_contours(np.pad(env, 1).astype(float), 0.5)
    c = max(cs, key=len)
    return dict(env=env, area=env.sum() * px_mm**2,
                per=np.sum(np.hypot(*np.diff(c, axis=0).T)) * px_mm,
                matfrac=(mat & env).sum() / env.sum(), contour=c - 1)


rows, thumbs = [], []
t0 = time.time()
for z1 in Z_L1:
    zi = int(z1 / 2**(LVL - 1))
    img = np.asarray(arr[zi, :, :]).astype(np.float32)
    e = envelope(img, PX)
    if e is None:
        print(f"altura {z1*0.01728:.0f} mm: sin rollo, salto"); continue
    row = dict(z_mm=z1 * 0.01728, area_mm2=e["area"], perim_mm=e["per"],
               materia=e["matfrac"])
    for s in S_LIST:
        L = e["area"] / s
        row[f"metros_s{s}"] = L / 1000
        row[f"vueltas_max_s{s}"] = 2 * L / (e["per"] + CORE_PER[0])
        row[f"vueltas_min_s{s}"] = 2 * L / (e["per"] + CORE_PER[1])
    rows.append(row); thumbs.append((img, e))
    print(f"altura {row['z_mm']:5.0f} mm | corte {e['area']:4.0f} mm² | "
          f"contorno {e['per']:4.0f} mm | materia {e['matfrac']:.0%} | "
          f"papel {row['metros_s0.17']:.1f} m | vueltas "
          f"{row['vueltas_min_s0.17']:.0f}-{row['vueltas_max_s0.17']:.0f} "
          f"(con hojas a 0,17 mm)   [{time.time()-t0:.0f} s]")

# ---- guardar tabla --------------------------------------------------
import csv
with open(f"{OUT}/carrete_1218.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

# ---- veredicto (fijado antes de correr) -----------------------------
# Con la separación MÁS favorable a muchas vueltas (0,164 mm) y el máximo de vueltas:
nmax = np.array([r["vueltas_max_s0.164"] for r in rows])
Lmax = np.array([r["metros_s0.164"] for r in rows])
print("\n" + "=" * 66)
print("RESUMEN (lo más generoso posible con '109 vueltas'):")
print(f"  papel por altura: {Lmax.min():.1f} a {Lmax.max():.1f} m (el 'telar' decía 8,4-9,4)")
print(f"  vueltas como MÁXIMO: {nmax.min():.0f} a {nmax.max():.0f}")
if (nmax < 95).sum() >= 0.75 * len(nmax) and (Lmax < 6).sum() >= 0.75 * len(Lmax):
    v = "109 VUELTAS NO CABEN en el corte. El telar de 8-9 m tampoco."
elif np.median(nmax) >= 100:
    v = "109 VUELTAS SÍ CABEN. El punto 1 de Claude era falso."
else:
    v = "SIN DECIDIR: el resultado queda entre medias."
print("VEREDICTO:", v)
print("Aviso: los huecos de aire cuentan como papel aquí, así que las cifras")
print("son un TECHO: el papel real solo puede ser igual o menor.")
print("=" * 66)

# ---- figura ---------------------------------------------------------
n = len(thumbs)
fig = plt.figure(figsize=(16, 13))
for i, ((img, e), r) in enumerate(zip(thumbs, rows)):
    ax = fig.add_subplot(4, 3, i + 1)
    ax.imshow(img, cmap="gray", vmax=np.percentile(img[img > 0], 99))
    c = e["contour"]; ax.plot(c[:, 1], c[:, 0], "r-", lw=1)
    ax.set_title(f"altura {r['z_mm']:.0f} mm — {r['metros_s0.17']:.1f} m, "
                 f"{r['vueltas_min_s0.17']:.0f}-{r['vueltas_max_s0.17']:.0f} vueltas", fontsize=9)
    ax.axis("off")
ax = fig.add_subplot(4, 1, 4)
zz = [r["z_mm"] for r in rows]
for s, col in zip(S_LIST, ["C3", "C1", "C2", "C0"]):
    lo = [r[f"vueltas_min_s{s}"] for r in rows]; hi = [r[f"vueltas_max_s{s}"] for r in rows]
    ax.fill_between(zz, lo, hi, color=col, alpha=0.2, label=f"hojas a {s} mm")
ax.axhline(109, color="k", ls="--", lw=1); ax.text(zz[0], 110, "109", fontsize=9)
ax.axhline(60, color="k", ls=":", lw=1); ax.text(zz[0], 61, "60", fontsize=9)
ax.set_xlabel("altura en el rollo (mm)"); ax.set_ylabel("vueltas que caben")
ax.legend(fontsize=8, loc="upper right")
plt.tight_layout()
plt.savefig(f"{OUT}/carrete_1218.png", dpi=130)
plt.show()
print(f"guardado en {OUT}: carrete_1218.csv y carrete_1218.png")
print("listo")

# =====================================================================
# CELDA "GRAVILLA" — PHerc1218
# 1) Mide lo blanco que es el relleno del centro (gravilla) comparado
#    con el papiro y con los granos brillantes sueltos.
# 2) Fija una regla para decir qué es gravilla y qué es papel.
# 3) Borra la gravilla en 5 rodajas y enseña antes / después.
# El veredicto está fijado antes de correr (ver PASO 2).
# Autónoma: pegar entera en una celda de Colab. ~5-10 min.
# Guarda gravilla_1218.png y gravilla_regla.json en Drive/vesuvius_1218/
# =====================================================================

import subprocess, sys, os, time, json
try:
    import zarr, s3fs
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "zarr", "s3fs"], check=True)
    import zarr, s3fs
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu

try:
    from google.colab import drive
    drive.mount("/content/drive")
    OUT = "/content/drive/MyDrive/vesuvius_1218"
except Exception:
    OUT = "./vesuvius_1218"
os.makedirs(OUT, exist_ok=True)

if "root" not in dir():
    VOLUME = ("vesuvius-challenge-open-data/PHerc1218/volumes/"
              "20250521120456-8.640um-1.2m-116keV-masked.zarr")
    root = zarr.open(s3fs.S3Map(VOLUME, s3=s3fs.S3FileSystem(anon=True)), mode="r")

LVL = 1                                   # 17 µm: se ven los granos
A = root[str(LVL)]
PX = 0.00864 * 2**LVL
HEIGHTS_MM = [22.0, 130.0, 150.0, 170.0, 185.0]   # donde se vio relleno en los cortes largos
CENTER_MM, CENTER_Z_MM = (34.0, 38.5), 105.0      # ombligo de Diego (validado el 22 sep)
SEARCH_MM = 8.0                                   # radio de búsqueda del relleno alrededor del ombligo
t0 = time.time()
say = lambda m: print(f"[{time.time()-t0:4.0f} s] {m}")


def read(z_mm):
    return np.asarray(A[int(round(z_mm / PX)), :, :]).astype(np.float32)


def silhouette_centre(img):
    y, x = np.nonzero(img > 0)
    return x.mean(), y.mean()


def disk(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return (xx**2 + yy**2) <= r * r


# ---- ombligo: tu punto a 105 mm, trasladado con el centro de la silueta
ref = read(CENTER_Z_MM)
rcx, rcy = silhouette_centre(ref)
off_x, off_y = CENTER_MM[0] / PX - rcx, CENTER_MM[1] / PX - rcy
del ref
say("ombligo de referencia listo")

# ---- PASO 1: muestras de las tres clases en cada rodaja ---------------
data = []
for z in HEIGHTS_MM:
    img = read(z)
    sx, sy = silhouette_centre(img)
    cx, cy = sx + off_x, sy + off_y
    mat_thr = threshold_otsu(img[img > 0])
    mat = img > mat_thr
    pap_vals = img[mat]
    hi = np.percentile(pap_vals, 99.5)
    bright = img > hi
    yy, xx = np.indices(img.shape)
    dist = np.hypot(xx - cx, yy - cy) * PX
    # RELLENO: región (no solo píxeles brillantes) alrededor del mayor grupo brillante cerca del ombligo
    # (solo en una ventana alrededor del ombligo: rápido)
    Rw = int((SEARCH_MM + 1) / PX)
    wy = slice(max(int(cy) - Rw, 0), int(cy) + Rw); wx = slice(max(int(cx) - Rw, 0), int(cx) + Rw)
    reg = ndi.binary_fill_holes(ndi.binary_closing(bright[wy, wx] & (dist[wy, wx] < SEARCH_MM),
                                                   disk(int(0.3 / PX))))
    lab, n = ndi.label(reg)
    fill = np.zeros_like(bright)
    if n:
        sizes = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)) * PX**2
        k = int(np.argmax(sizes)) + 1
        if sizes[k - 1] >= 0.3:                     # al menos 0,3 mm²
            fill[wy, wx] = lab == k
    # GRANOS: grupos brillantes diminutos lejos del ombligo
    far = pap_vals[::7]
    med = np.median(far); mad = 1.4826 * np.median(np.abs(far - med))
    very = img > med + 6 * mad                      # muy por encima del ruido del papiro
    labb, nb = ndi.label(very & (dist > SEARCH_MM + 2))
    gsz = ndi.sum(np.ones_like(labb), labb, index=np.arange(1, nb + 1)) * PX**2 if nb else np.array([])
    keep = np.zeros(nb + 1, bool)
    if nb: keep[1:] = gsz < 0.02
    small = keep[labb]
    # PAPIRO: materia lejos del ombligo, sin granos
    pap = mat & (dist > SEARCH_MM + 2) & ~ndi.binary_dilation(small, iterations=2)
    # textura: rugosidad fina (desviación local en 0,1 mm)
    w = max(3, int(0.1 / PX))
    m1 = ndi.uniform_filter(img, w); m2 = ndi.uniform_filter(img * img, w)
    rough = np.sqrt(np.clip(m2 - m1 * m1, 0, None))
    d = dict(z=z, img=img, cx=cx, cy=cy, fill=fill, grains=small, pap=pap, rough=rough,
             fill_mm2=fill.sum() * PX**2)
    data.append(d)
    say(f"altura {z:.0f} mm: relleno {d['fill_mm2']:.1f} mm², "
        f"granos {int(small.sum())} píxeles")

cat = lambda key: np.concatenate([d["img"][d[key]] for d in data if d[key].any()])
catr = lambda key: np.concatenate([d["rough"][d[key]] for d in data if d[key].any()])
P, F, G = cat("pap"), cat("fill"), cat("grains")
mP, mF, mG = np.median(P), np.median(F), np.median(G)
rP, rF = np.median(catr("pap")), np.median(catr("fill"))

# ---- PASO 2: veredicto (fijado antes de correr) ------------------------
# regla de brillo: el umbral que mejor separa papiro de relleno
cand = np.linspace(np.percentile(P, 50), np.percentile(F, 90), 200)
err = [np.mean(P > t) + np.mean(F <= t) for t in cand]
T = float(cand[int(np.argmin(err))])
pap_over, fill_under = float(np.mean(P > T)), float(np.mean(F <= T))
separable = pap_over < 0.01 and fill_under < 0.20
closer_to = "GRANOS (mineral)" if abs(mF - mG) < abs(mF - mP) else "PAPIRO (papel hecho polvo)"

print("\n" + "=" * 66)
print("BRILLO MEDIO (mediana):")
print(f"  papiro          {mP:6.1f}")
print(f"  relleno central {mF:6.1f}   ({mF/mP:.2f} veces el papiro)")
print(f"  granos sueltos  {mG:6.1f}   ({mG/mP:.2f} veces el papiro)")
print(f"RUGOSIDAD fina: relleno {rF:.1f} frente a papiro {rP:.1f} ({rF/rP:.2f} veces)")
print(f"\n1) El relleno se parece más a: {closer_to}")
print(f"2) ¿Se separa solo por brillo? {'SÍ' if separable else 'NO del todo'} — con la regla "
      f"'más brillante que {T:.0f}': se lleva {pap_over:.1%} del papiro y deja {fill_under:.0%} del relleno")
if not separable:
    print("   -> hará falta añadir la textura (granos frente a láminas) a la regla")
print("   (la regla solo se aplica junto al ombligo; en el resto del rollo solo se")
print("    borran los granos sueltos, así que el papiro de fuera no se toca)")
print("Aviso: el relleno se localiza por su parte brillante, así que su brillo")
print("sale algo favorecido. Mira las imágenes: el contorno rojo debe abarcar la gravilla.")
print("=" * 66)

# ---- PASO 3: borrar la gravilla y enseñar antes / después --------------
fig, axs = plt.subplots(len(data), 3, figsize=(15, 5 * len(data)))
R = int(10.0 / PX)
for row, d in zip(axs, data):
    img = d["img"]
    Rw = int((SEARCH_MM + 2) / PX)
    wy = slice(max(int(d["cy"]) - Rw, 0), int(d["cy"]) + Rw); wx = slice(max(int(d["cx"]) - Rw, 0), int(d["cx"]) + Rw)
    near = np.zeros_like(d["fill"])
    near[wy, wx] = ndi.binary_dilation(d["fill"][wy, wx], disk(int(0.5 / PX)))
    grav = (img > T) & near                                                # gravilla central
    grav |= d["grains"]                                                    # y granos sueltos
    clean = img.copy(); clean[grav] = np.median(img[(img > 0) & (img < threshold_otsu(img[img > 0]))])
    d["grav_frac"] = grav.sum() / (img > 0).sum()
    y0, x0 = int(d["cy"]) - R, int(d["cx"]) - R
    sl = (slice(max(y0, 0), y0 + 2 * R), slice(max(x0, 0), x0 + 2 * R))
    v = img[sl][img[sl] > 0]; lo, hi2 = np.percentile(v, 1), np.percentile(v, 99.7)
    row[0].imshow(img[sl], cmap="gray", vmin=lo, vmax=hi2); row[0].set_title(f"{d['z']:.0f} mm — original")
    row[1].imshow(img[sl], cmap="gray", vmin=lo, vmax=hi2)
    row[1].contour(d["fill"][sl], [0.5], colors="r", linewidths=1)
    gy, gx = np.nonzero(grav[sl]); row[1].plot(gx, gy, ",", color="yellow")
    row[1].set_title("rojo = relleno encontrado; amarillo = lo que se borra")
    row[2].imshow(clean[sl], cmap="gray", vmin=lo, vmax=hi2); row[2].set_title("limpia")
    for a in row: a.axis("off")
plt.tight_layout(); plt.savefig(f"{OUT}/gravilla_1218.png", dpi=110); plt.show()

fig, ax = plt.subplots(figsize=(10, 4))
bins = np.linspace(np.percentile(P, 0.5), max(np.percentile(G, 99.5), np.percentile(F, 99.5)), 120)
for arr_, lab_, c in [(P, "papiro", "C0"), (F, "relleno central", "C3"), (G, "granos sueltos", "C1")]:
    ax.hist(arr_, bins, density=True, histtype="step", lw=2, color=c, label=lab_)
ax.axvline(T, color="k", ls="--", label="regla")
ax.set_xlabel("brillo en el escáner"); ax.legend(); ax.set_yticks([])
plt.tight_layout(); plt.savefig(f"{OUT}/gravilla_brillos.png", dpi=110); plt.show()

print("\nParte de cada rodaja que se borra:")
for d in data:
    print(f"  {d['z']:5.0f} mm: {d['grav_frac']:.2%}")
json.dump(dict(level=LVL, threshold=T, median_papiro=float(mP), median_relleno=float(mF),
               median_granos=float(mG), separable=bool(separable), parecido=closer_to,
               alturas_mm=HEIGHTS_MM), open(f"{OUT}/gravilla_regla.json", "w"), indent=1)
print(f"Guardado en {OUT}: gravilla_1218.png, gravilla_brillos.png, gravilla_regla.json")
print("listo")

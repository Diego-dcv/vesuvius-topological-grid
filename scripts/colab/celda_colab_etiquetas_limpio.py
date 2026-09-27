# =====================================================================
# CELDA "ETIQUETAS SOBRE LO LIMPIO" — PHerc1218
# Pone las etiquetas de J (sus cruces de hoja, tabla pública) encima de
# las rodajas del escáner sin gravilla, en las 4 alturas de la zona recta
# (110, 120, 130, 140 mm), y responde:
#   1) ¿caen sobre hojas, sobre la gravilla, o fuera del borde?
#   2) contando SUS etiquetas hacia arriba y hacia abajo, ¿sale la misma
#      asimetría que nuestro contador (arriba ~60, abajo menos)?
# Autónoma: pegar entera en Colab. ~5-10 min.
# Guarda en Drive/vesuvius_1218/etiquetas_limpio/
# =====================================================================

import subprocess, sys, os, time, io, gzip, urllib.request
try:
    import zarr, s3fs
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "zarr", "s3fs"], check=True)
    import zarr, s3fs
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu

try:
    from google.colab import drive
    drive.mount("/content/drive")
    OUT = "/content/drive/MyDrive/vesuvius_1218/etiquetas_limpio"
except Exception:
    OUT = "./vesuvius_1218/etiquetas_limpio"
os.makedirs(OUT, exist_ok=True)

if "root" not in dir():
    VOLUME = ("vesuvius-challenge-open-data/PHerc1218/volumes/"
              "20250521120456-8.640um-1.2m-116keV-masked.zarr")
    root = zarr.open(s3fs.S3Map(VOLUME, s3=s3fs.S3FileSystem(anon=True)), mode="r")

RAW = ("https://raw.githubusercontent.com/Jinhojeong/vesuvius-surface-geometry-diagnostic/"
       "main/results/kollesis/")
HEIGHTS_MM = [110.0, 120.0, 130.0, 140.0]
CENTER_MM, CENTER_Z_MM = (34.0, 38.5), 105.0     # ombligo de Diego
VOX = 0.01728                                    # mm por píxel en nivel 1 (el de la tabla)
DX, DY = -3, -1                                  # marco de etiquetas -> marco del escáner
# nuestro contador (celda contar_vueltas, 23 sep), para comparar
NUESTRO = {110.0: (60.7, 49.5), 120.0: (62.7, 45.3), 130.0: (60.2, 41.2), 140.0: (58.5, 38.0)}
A1 = root["1"]
t0 = time.time()
say = lambda m: print(f"[{time.time()-t0:4.0f} s] {m}")

# ---- tabla de J y sus orígenes -----------------------------------------
if "tab" not in dir():
    tab = pd.read_csv(io.BytesIO(urllib.request.urlopen(RAW + "positions_merged.csv.gz").read()),
                      compression="gzip")
    org = pd.read_csv(io.BytesIO(urllib.request.urlopen(RAW + "origins_merged.csv").read()))
    org = org.groupby(org["z"].astype(float).astype(int))[["cx", "cy"]].mean()
say(f"tabla de J: {len(tab):,} cruces")
zs = np.array(sorted(tab["z"].unique()))


def centre_axis(img):
    y, x = np.nonzero(img > 0)
    cx, cy = x.mean(), y.mean()
    dx, dy = x - cx, y - cy
    ang = 0.5 * np.arctan2(2 * (dx * dy).mean(), (dx * dx).mean() - (dy * dy).mean())
    return cx, cy, ang


def read1(z_idx):
    """rodaja de nivel 1 recortada al rollo; devuelve (imagen, y0, x0)."""
    a = np.asarray(A1[int(z_idx), :, :])
    ys, xs = np.nonzero(a > 0)
    y0, x0 = max(ys.min() - 60, 0), max(xs.min() - 60, 0)
    return a[y0:ys.max() + 60, x0:xs.max() + 60].astype(np.float32), y0, x0


ref, ry0, rx0 = read1(round(CENTER_Z_MM / VOX))
rcx, rcy, _ = centre_axis(ref); rcx += rx0; rcy += ry0
offx, offy = CENTER_MM[0] / VOX - rcx, CENTER_MM[1] / VOX - rcy
del ref
say("ombligo de referencia listo")


def clean_core(img, cx, cy, search_mm=6.0):
    """borra la mancha de gravilla junto al ombligo (misma regla del 22 sep, algo más estricta)."""
    v = img[img > 0]; mat = img > threshold_otsu(v); pap = img[mat]
    med = np.median(pap); mad = 1.4826 * np.median(np.abs(pap[::7] - med))
    R = int(search_mm / VOX); y0, x0 = max(int(cy) - R, 0), max(int(cx) - R, 0)
    win = img[y0:int(cy) + R, x0:int(cx) + R]
    yy, xx = np.indices(win.shape)
    d = np.hypot(xx + x0 - cx, yy + y0 - cy) * VOX
    r = int(0.3 / VOX); ky, kx = np.mgrid[-r:r + 1, -r:r + 1]
    reg = ndi.binary_fill_holes(ndi.binary_closing((win > med + 2.5 * mad) & (d < search_mm),
                                                   (kx**2 + ky**2) <= r * r))
    lab, n = ndi.label(reg)
    out = img.copy(); gm = np.zeros(img.shape, bool)
    if n:
        idx = np.arange(1, n + 1)
        sz = ndi.sum(np.ones_like(lab), lab, idx) * VOX**2
        mdn = ndi.median(win, lab, idx)
        ok = (sz >= 0.3) & (mdn >= 1.15 * med)
        if ok.any():
            m = lab == idx[ok][np.argmax(sz[ok])]
            out[y0:y0 + win.shape[0], x0:x0 + win.shape[1]][m] = np.percentile(v, 2)
            gm[y0:y0 + win.shape[0], x0:x0 + win.shape[1]] = m
    return out, gm


def merge_split(r):
    """junta etiquetas partidas (< 7 píxeles, la regla medida en agosto)."""
    r = np.sort(r); keep = [r[0]] if len(r) else []
    for x in r[1:]:
        if x - keep[-1] >= 7: keep.append(x)
        else: keep[-1] = 0.5 * (keep[-1] + x)
    return np.array(keep)


rows = []
for H in HEIGHTS_MM:
    z = int(zs[np.argmin(np.abs(zs - H / VOX))])
    img, oy, ox = read1(z)
    scx, scy, ang = centre_axis(img)
    dcx, dcy = scx + offx, scy + offy                        # ombligo de Diego (px del recorte)
    img, gmask = clean_core(img, dcx, dcy)
    p = tab[tab["z"] == z]
    jcx, jcy = org.loc[org.index[np.argmin(np.abs(org.index.values - z))]] + np.array([DX - ox, DY - oy])
    th = np.deg2rad(p["theta_deg"].values); rr = p["r_l1_vox"].values
    X = jcx + rr * np.cos(th); Y = jcy + rr * np.sin(th)
    # dónde caen: sobre papel, sobre la gravilla, o fuera del rollo
    ix = np.clip(np.round(X).astype(int), 0, img.shape[1] - 1)
    iy = np.clip(np.round(Y).astype(int), 0, img.shape[0] - 1)
    inside = img[iy, ix] > 0
    on_grav = gmask[iy, ix]
    # contar SUS etiquetas por sus rayos más cercanos al eje corto (arriba y abajo)
    u = np.array([-np.sin(ang), np.cos(ang)])
    if u[1] > 0: u = -u                                      # arriba en la imagen
    counts = {}
    for side, vec in (("ARRIBA", u), ("ABAJO", -u)):
        a = np.degrees(np.arctan2(vec[1], vec[0])) % 360
        thetas = np.sort(p["theta_deg"].unique())
        dd = np.abs((thetas - a + 180) % 360 - 180)
        near = thetas[np.argsort(dd)[:3]]                    # 3 rayos más cercanos
        c = [len(merge_split(p[p["theta_deg"] == t]["r_l1_vox"].values)) for t in near]
        counts[side] = (np.median(c), min(c), max(c))
    rows.append(dict(H=H, z=z, n=len(p), fuera=(~inside).mean(), grava=on_grav.mean(),
                     up=counts["ARRIBA"], down=counts["ABAJO"]))
    # figura: rodaja limpia con las etiquetas encima
    ys, xs = np.nonzero(img > 0)
    y0, y1, x0, x1 = ys.min() - 40, ys.max() + 40, xs.min() - 40, xs.max() + 40
    vv = img[img > 0]
    fig, axs = plt.subplots(1, 2, figsize=(18, 8), gridspec_kw=dict(width_ratios=[2, 1]))
    for k, ax in enumerate(axs):
        ax.imshow(img, cmap="gray", vmin=np.percentile(vv, 1), vmax=np.percentile(vv, 99.5))
        ax.scatter(X, Y, s=2 if k == 0 else 8, c="r", lw=0)
        ax.contour(gmask, [0.5], colors="y", linewidths=1)
        ax.plot(dcx, dcy, "w+", ms=18, mew=2); ax.plot(jcx, jcy, "c+", ms=18, mew=2)
        for vec in (u, -u):
            ax.plot([dcx, dcx + vec[0] * 900], [dcy, dcy + vec[1] * 900], "g-", lw=0.8)
    axs[0].set_xlim(x0, x1); axs[0].set_ylim(y1, y0)
    w = int(3 / VOX)
    axs[1].set_xlim(dcx - w, dcx + w); axs[1].set_ylim(dcy + w, dcy - w)
    axs[0].set_title(f"{H:.0f} mm: rojo = etiquetas de J; blanca = tu ombligo; azul = origen de J; "
                     f"amarillo = gravilla borrada; verde = eje corto", fontsize=9)
    axs[1].set_title("zoom 6 mm alrededor del ombligo", fontsize=9)
    for a in axs: a.axis("off")
    plt.tight_layout(); plt.savefig(f"{OUT}/etiquetas_{int(H)}.png", dpi=150)
    if H == 130.0: plt.show()
    else: plt.close()
    # zoom del borde de ABAJO, donde faltan vueltas
    ex, ey = dcx - u[0] * 0, dcy - u[1] * 0
    tt = np.arange(0, 900); px_ = (dcx - u[0] * tt).astype(int); py_ = (dcy - u[1] * tt).astype(int)
    ok_ = (px_ >= 0) & (py_ >= 0) & (px_ < img.shape[1]) & (py_ < img.shape[0])
    last = np.where(img[py_[ok_], px_[ok_]] > 0)[0]
    if last.size:
        bx, by = px_[ok_][last.max()], py_[ok_][last.max()]
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(img, cmap="gray", vmin=np.percentile(vv, 1), vmax=np.percentile(vv, 99.5))
        ax.scatter(X, Y, s=10, c="r", lw=0)
        ax.set_xlim(bx - w, bx + w); ax.set_ylim(by + w, by - w); ax.axis("off")
        ax.set_title(f"{H:.0f} mm: borde de ABAJO (6 mm) con las etiquetas de J", fontsize=9)
        plt.tight_layout(); plt.savefig(f"{OUT}/borde_abajo_{int(H)}.png", dpi=150)
        if H == 130.0: plt.show()
        else: plt.close()
    del img
    say(f"altura {H:.0f} mm hecha")

print("\n" + "=" * 70)
print("DÓNDE CAEN LAS ETIQUETAS DE J")
for r in rows:
    print(f"  {r['H']:.0f} mm: {r['n']} etiquetas | fuera del rollo {r['fuera']:.1%} | "
          f"sobre la gravilla {r['grava']:.1%}")
print("\nCUÁNTAS HOJAS VEN SUS ETIQUETAS POR EL EJE CORTO (3 rayos, sin partidas)")
print("  altura | J arriba | J abajo || nuestro arriba | nuestro abajo")
for r in rows:
    nu, nd = NUESTRO[r["H"]]
    print(f"  {r['H']:5.0f}  | {r['up'][0]:5.0f} ({r['up'][1]}-{r['up'][2]}) | "
          f"{r['down'][0]:5.0f} ({r['down'][1]}-{r['down'][2]}) || {nu:8.0f} | {nd:8.0f}")
print("Ojo: las etiquetas de J no ven todas las hojas (le faltan ~1/3), así que sus")
print("números serán más bajos. Lo que importa es si también ven MÁS arriba que abajo.")
print("=" * 70)
print(f"Guardado en {OUT}: etiquetas_<altura>.png y borde_abajo_<altura>.png")
print("listo")

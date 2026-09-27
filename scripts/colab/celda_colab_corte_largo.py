# =====================================================================
# CELDA "CORTE A LO LARGO" — PHerc1218
# Corta el rollo de arriba abajo (no en rodajas) en 4 direcciones y
# amplía los dos extremos. Sirve para mirar A OJO si el papel se
# arrastró hacia los extremos:
#   - líneas rectas hasta el borde  -> no hubo arrastre
#   - zigzag / acordeón cerca del extremo -> papel empujado y arrugado
#   - cono (las vueltas de dentro asoman más que las de fuera) -> capas resbaladas
# El corte pasa por el centro de Diego (ombligo real a 105 mm) y lo sigue en
# altura junto con el centro de la silueta: si el rollo está torcido, se tuerce con él.
# Autónoma: pegar entera en una celda de Colab. ~10-20 min.
# Guarda las figuras en Drive/vesuvius_1218/corte_largo/
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

try:
    from google.colab import drive
    drive.mount("/content/drive")
    OUT = "/content/drive/MyDrive/vesuvius_1218/corte_largo"
except Exception:
    OUT = "./vesuvius_1218/corte_largo"
os.makedirs(OUT, exist_ok=True)

if "root" not in dir():
    VOLUME = ("vesuvius-challenge-open-data/PHerc1218/volumes/"
              "20250521120456-8.640um-1.2m-116keV-masked.zarr")
    root = zarr.open(s3fs.S3Map(VOLUME, s3=s3fs.S3FileSystem(anon=True)), mode="r")

levels = sorted(int(k) for k in root.keys() if str(k).isdigit())
LC = max(l for l in levels if l <= 5)          # muy grueso: silueta y extremos
LO = 3 if 3 in levels else 2                   # vista completa
LZ = 2 if 2 in levels else 1                   # extremos ampliados
PX = lambda L: 0.00864 * 2**L                  # mm por píxel
R_MM = 32.0                                    # medio ancho del corte
END_IN_MM, END_OUT_MM = 13.0, 2.0              # zoom: 13 mm hacia dentro, 2 hacia fuera
# CENTRO DE DIEGO: el ombligo real hallado a ojo sobre la sección con cuadrícula
# (x, y en mm de la cuadrícula; y hacia abajo como en la imagen) y la altura de esa sección.
# El corte pasa por ese punto y lo sigue en altura con el mismo desplazamiento respecto
# al centro de la silueta. Poner CENTER_MM = None para usar solo el centro de la silueta.
CENTER_MM = (34.0, 38.5)
CENTER_Z_MM = 105.0
# LIMPIAR = True borra la gravilla del ombligo y los granos sueltos antes de cortar
# (regla del 22 sep: la mancha entera dentro de su contorno + granos diminutos muy brillantes)
LIMPIAR = True
SEARCH_MM = 8.0
SUF = "_limpio" if LIMPIAR else ""
t0 = time.time()
say = lambda m: print(f"[{time.time()-t0:5.0f} s] {m}")

# ---- 1. silueta gruesa: dónde está el rollo y dónde acaba ------------
C = np.asarray(root[str(LC)][:])
mask = C > 0
area = mask.sum(axis=(1, 2))
ref = np.median(area[area > 0])
good = np.where(area > 0.2 * ref)[0]
zc0, zc1 = good[0], good[-1]
yy, xx = np.where(mask[zc0:zc1 + 1].any(0))
m = int(np.ceil(2.0 / PX(LC)))
yc0, yc1 = max(yy.min() - m, 0), min(yy.max() + m, C.shape[1] - 1)
xc0, xc1 = max(xx.min() - m, 0), min(xx.max() + m, C.shape[2] - 1)
say(f"rollo entre alturas {zc0*PX(LC):.0f} y {zc1*PX(LC):.0f} mm")

# ---- 2. vista completa (nivel LO) -------------------------------------
f = 2**(LC - LO)
A = root[str(LO)]
za, zb = max(zc0 * f - 20, 0), min((zc1 + 1) * f + 20, A.shape[0])
ya, yb, xa, xb = yc0 * f, min((yc1 + 1) * f, A.shape[1]), xc0 * f, min((xc1 + 1) * f, A.shape[2])
O = np.zeros((zb - za, yb - ya, xb - xa), dtype=A.dtype)
step = 256
for z in range(za, zb, step):
    O[z - za:min(z + step, zb) - za] = np.asarray(A[z:min(z + step, zb), ya:yb, xa:xb])
say(f"vista completa leída: {O.shape}, {O.nbytes/1e9:.1f} GB")

# centro y orientación por altura (sigue al rollo aunque esté torcido)
nz = O.shape[0]
cy = np.full(nz, np.nan); cx = np.full(nz, np.nan); ang = np.full(nz, np.nan)
for i in range(nz):
    mk = O[i] > 0
    if mk.sum() < 0.2 * ref * f * f:
        continue
    y, x = np.nonzero(mk)
    cy[i], cx[i] = y.mean(), x.mean()
    dy, dx = y - cy[i], x - cx[i]
    ang[i] = 0.5 * np.arctan2(2 * (dx * dy).mean(), (dx * dx).mean() - (dy * dy).mean())
ok = ~np.isnan(cy)
idx = np.arange(nz)
w = max(3, int(3.0 / PX(LO)))                  # suavizado de 3 mm
cy = ndi.uniform_filter1d(np.interp(idx, idx[ok], cy[ok]), w)
cx = ndi.uniform_filter1d(np.interp(idx, idx[ok], cx[ok]), w)
# -- pasar el corte por el centro de Diego (con imagen de comprobación) --
if CENTER_MM is not None:
    iz = int(round(CENTER_Z_MM / PX(LO))) - za
    px_x = CENTER_MM[0] / PX(LO) - xa
    px_y = CENTER_MM[1] / PX(LO) - ya
    ddx, ddy = px_x - cx[iz], px_y - cy[iz]
    print(f"centro de Diego a {np.hypot(ddx, ddy)*PX(LO):.1f} mm del centro de la silueta "
          f"(a {CENTER_Z_MM:.0f} mm de altura)")
    fig, ax = plt.subplots(figsize=(7, 7))
    sl = O[iz].astype(np.float32); v = sl[sl > 0]
    ax.imshow(sl, cmap="gray", vmin=np.percentile(v, 1), vmax=np.percentile(v, 99.5),
              extent=[xa * PX(LO), xb * PX(LO), yb * PX(LO), ya * PX(LO)])
    ax.plot(*CENTER_MM, "r+", ms=25, mew=2, label="centro de Diego")
    ax.plot((cx[iz] + xa) * PX(LO), (cy[iz] + ya) * PX(LO), "c+", ms=25, mew=2,
            label="centro de la silueta")
    ax.legend(); ax.set_title(f"COMPROBACIÓN: sección a {CENTER_Z_MM:.0f} mm (ejes en mm)")
    plt.savefig(f"{OUT}/comprobacion_centro.png", dpi=130); plt.show()
    print("MIRA LA IMAGEN: la cruz roja debe caer en el ombligo. Si cae fuera, "
          "la cuadrícula usaba otros ejes: para aquí y avisa.")
    cx = cx + ddx; cy = cy + ddy
phi0 = 0.5 * np.angle(np.mean(np.exp(2j * ang[ok])))   # dirección de las alas
CUTS = [("a lo largo de las alas", 0), ("diagonal 45°", 45),
        ("eje corto (hojas planas)", 90), ("diagonal 135°", 135)]


def cut(vol, cyv, cxv, px_mm, deg):
    """plano vertical por el centro de cada altura, girado deg respecto a las alas."""
    a = phi0 + np.deg2rad(deg)
    t = np.arange(-R_MM, R_MM, px_mm) / px_mm
    out = np.zeros((vol.shape[0], t.size), np.float32)
    for i in range(vol.shape[0]):
        ys = cyv[i] + t * np.sin(a); xs = cxv[i] + t * np.cos(a)
        out[i] = ndi.map_coordinates(vol[i].astype(np.float32), [ys, xs], order=1, cval=0)
    return out


def show(ax, img, px_mm, z0_mm, title):
    v = img[img > 0]
    lo, hi = (np.percentile(v, 1), np.percentile(v, 99.5)) if v.size else (0, 1)
    ax.imshow(img, cmap="gray", vmin=lo, vmax=hi, origin="lower", aspect="equal",
              extent=[-R_MM, R_MM, z0_mm, z0_mm + img.shape[0] * px_mm])
    ax.set_title(title, fontsize=9)




def disk(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return (xx**2 + yy**2) <= r * r


def limpiar(sl, cxs, cys, px):
    """borra en una rodaja la mancha de gravilla junto al ombligo y los granos sueltos."""
    v = sl[sl > 0]
    if v.size < 1000:
        return sl, 0.0
    mat = sl > threshold_otsu(v)
    pap = sl[mat].astype(np.float32)
    med = np.median(pap); mad = 1.4826 * np.median(np.abs(pap[::5] - med)); hi = med + 2.5 * mad
    air = np.percentile(v, 2)
    out = sl.copy()
    R = int((SEARCH_MM + 1) / px)
    y0, x0 = max(int(cys) - R, 0), max(int(cxs) - R, 0)
    win = sl[y0:int(cys) + R, x0:int(cxs) + R]
    yy, xx = np.indices(win.shape)
    dd = np.hypot(xx + x0 - cxs, yy + y0 - cys) * px
    reg = ndi.binary_fill_holes(ndi.binary_closing((win > hi) & (dd < SEARCH_MM), disk(max(1, int(0.3 / px)))))
    lab, n = ndi.label(reg)
    area = 0.0
    if n:
        idx = np.arange(1, n + 1)
        sizes = ndi.sum(np.ones_like(lab), lab, idx) * px**2
        meds = ndi.median(win, lab, idx)
        ok = (sizes >= 0.3) & (meds >= 1.1 * med)       # mancha de verdad, no motas de papiro
        if ok.any():
            k = idx[ok][np.argmax(sizes[ok])]
            m = ndi.binary_dilation(lab == k, disk(max(1, int(0.1 / px))))
            out[y0:y0 + win.shape[0], x0:x0 + win.shape[1]][m] = air
            area = m.sum() * px**2
    lb, nb = ndi.label(sl > med + 6 * mad)
    if nb:
        small = np.bincount(lb.ravel()) * px**2 < 0.02
        small[0] = False
        out[small[lb]] = air
    return out, area

views_orig = [(name, cut(O, cy, cx, PX(LO), d)) for name, d in CUTS if d in (90, 135)]
fill_area = np.zeros(O.shape[0])
if LIMPIAR:
    for i in range(O.shape[0]):
        O[i], fill_area[i] = limpiar(O[i], cx[i], cy[i], PX(LO))
    say("gravilla borrada en la vista completa")
views = [(name, cut(O, cy, cx, PX(LO), d)) for name, d in CUTS]
say("cortes completos hechos")
fig, axs = plt.subplots(1, 4, figsize=(16, 14))
for ax, (name, img) in zip(axs, views):
    show(ax, img, PX(LO), za * PX(LO), name)
    ax.set_xlabel("mm desde el centro")
axs[0].set_ylabel("altura en el rollo (mm)")
plt.suptitle("PHerc1218 — cortes de arriba abajo por el centro del rollo" + (" (SIN gravilla)" if LIMPIAR else ""))
plt.tight_layout()
plt.savefig(f"{OUT}/corte_largo_vista{SUF}.png", dpi=150)
plt.show()

if LIMPIAR:
    fig, axs = plt.subplots(1, 5, figsize=(20, 14),
                            gridspec_kw=dict(width_ratios=[1, 1, 1, 1, 0.6]))
    k = 0
    for name, d in CUTS:
        if d not in (90, 135):
            continue
        img_o = dict(views_orig)[name]; img_l = dict(views)[name]
        show(axs[k], img_o, PX(LO), za * PX(LO), f"{name}\nANTES"); k += 1
        show(axs[k], img_l, PX(LO), za * PX(LO), f"{name}\nDESPUÉS"); k += 1
    zz = (za + np.arange(O.shape[0])) * PX(LO)
    axs[4].plot(ndi.uniform_filter1d(fill_area, 15), zz, "r")
    axs[4].set_ylim(zz[0], zz[-1]); axs[4].set_xlabel("mm² de gravilla por rodaja")
    axs[4].set_title("dónde está la gravilla")
    plt.tight_layout(); plt.savefig(f"{OUT}/gravilla_antes_despues.png", dpi=150); plt.show()
    del views_orig

# guardar datos de centro para los extremos y soltar memoria
g = 2**(LO - LZ)
zi = np.arange(nz)
del O

# ---- 3. los dos extremos ampliados (nivel LZ) ------------------------
B = root[str(LZ)]
# ventanas a ampliar (alturas en mm, leídas de la vista completa del 22 sep).
# Los extremos automáticos cogían la base del soporte y trozos sueltos, no el rollo.
WINDOWS = [("extremo BAJO del rollo", 6.0, 22.0),
           ("zona ARRUGADA", 50.0, 70.0),
           ("zona RECTA", 120.0, 140.0),
           ("extremo ALTO del rollo", 180.0, 196.0)]
for label, zlo_mm, zhi_mm in WINDOWS:
    z0 = max(int(zlo_mm / PX(LZ)), 0); z1 = min(int(zhi_mm / PX(LZ)), B.shape[0])
    if z1 - z0 < 10:
        print(f'{label}: fuera del escáner, salto'); continue
    S = np.zeros((z1 - z0, yb * g - ya * g, xb * g - xa * g), dtype=B.dtype)
    part = np.asarray(B[z0:z1, ya * g:min(yb * g, B.shape[1]), xa * g:min(xb * g, B.shape[2])])
    S[:, :part.shape[1], :part.shape[2]] = part; del part
    # centro: el de la vista completa, pasado a este nivel
    zo = (np.arange(z0, z1) / g) - za
    cyz = np.interp(zo, zi, cy) * g; cxz = np.interp(zo, zi, cx) * g
    if LIMPIAR:
        for i in range(S.shape[0]):
            S[i], _ = limpiar(S[i], cxz[i], cyz[i], PX(LZ))
    # comprobación: por dónde pasan los cortes en una rodaja 5 mm hacia dentro del extremo
    k = S.shape[0] // 2
    sl = S[k].astype(np.float32); v = sl[sl > 0]
    figc, axc = plt.subplots(figsize=(7, 7))
    axc.imshow(sl, cmap="gray", vmin=np.percentile(v, 1), vmax=np.percentile(v, 99.5),
               extent=[xa * g * PX(LZ), xb * g * PX(LZ), yb * g * PX(LZ), ya * g * PX(LZ)])
    c0x, c0y = (cxz[k] + xa * g) * PX(LZ), (cyz[k] + ya * g) * PX(LZ)
    for (name, d), col in zip(CUTS, ["r", "y", "c", "m"]):
        a = phi0 + np.deg2rad(d)
        axc.plot([c0x - R_MM * np.cos(a), c0x + R_MM * np.cos(a)],
                 [c0y - R_MM * np.sin(a), c0y + R_MM * np.sin(a)], col, lw=1, label=name)
    axc.plot(c0x, c0y, "w+", ms=20, mew=2)
    axc.set_xlim(xa * g * PX(LZ), xb * g * PX(LZ)); axc.set_ylim(yb * g * PX(LZ), ya * g * PX(LZ))
    axc.legend(fontsize=7); axc.set_title(f"{label}: por dónde pasan los cortes (ejes en mm)")
    tag = label.split()[-1].lower() if "extremo" in label else label.split()[-1].lower()
    tag = {"rollo": ("bajo" if "BAJO" in label else "alto")}.get(tag, tag)
    plt.savefig(f"{OUT}/comprobacion_cortes_{tag}{SUF}.png", dpi=130); plt.show()
    fig, axs = plt.subplots(4, 1, figsize=(15, 16))
    for ax, (name, d) in zip(axs, CUTS):
        img = cut(S, cyz, cxz, PX(LZ), d)
        show(ax, img, PX(LZ), z0 * PX(LZ), f"{label} — {name}")
        ax.set_ylabel("altura (mm)")
        plt.imsave(f"{OUT}/{tag}_{d:03d}{SUF}.png",
                   np.flipud(img), cmap="gray",
                   vmin=np.percentile(img[img > 0], 1), vmax=np.percentile(img[img > 0], 99.5))
    axs[-1].set_xlabel("mm desde el centro")
    plt.tight_layout()
    plt.savefig(f"{OUT}/corte_largo_{tag}{SUF}.png", dpi=170)
    plt.show()
    del S
    say(f"{label} hecho")

print("\nANTES DE MIRAR: en cada comprobacion_cortes_* la cruz blanca debe caer en el ombligo.")
print("Si no cae, dime dónde está el ombligo en esa rodaja (x, y en mm) y lo corrijo.")
print("\nQUÉ MIRAR en los extremos ampliados:")
print("  líneas verticales rectas hasta el borde -> no hubo arrastre")
print("  zigzag o acordeón cerca del borde       -> papel empujado y arrugado")
print("  borde en punta o cono (las del centro     ")
print("  asoman más que las de fuera)            -> capas resbaladas")
print(f"Guardado en {OUT} (las imágenes <zona>_*.png son a tamaño real para ampliar)")
print("listo")

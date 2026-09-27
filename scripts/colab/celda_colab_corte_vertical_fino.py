# =====================================================================
# CELDA "CORTE VERTICAL FINO PARA CONTAR" — PHerc1218
# El mismo corte vertical del eje corto, pero a MÁXIMA resolución
# (8,6 micras por píxel) y solo en la zona recta: de 120 a 124 mm de
# altura, desde el ombligo hasta el borde, hacia ARRIBA y hacia ABAJO.
# En este corte las hojas se ven como rayas verticales. Se enseña en
# tiras de 2 mm a proporción real, con una regla de 0,17 mm (una hoja
# según nuestra medida) y marcas cada 0,1 mm, para contar a ojo.
# El contador automático da su cifra al final, SOLO para comparar
# después de que hayas contado tú.
# Autónoma: pegar entera en Colab. ~10-20 min (lee un bloque fino).
# Guarda en Drive/vesuvius_1218/corte_fino/
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
from scipy.signal import hilbert

try:
    from google.colab import drive
    drive.mount("/content/drive")
    OUT = "/content/drive/MyDrive/vesuvius_1218/corte_fino"
except Exception:
    OUT = "./vesuvius_1218/corte_fino"
os.makedirs(OUT, exist_ok=True)

if "root" not in dir():
    VOLUME = ("vesuvius-challenge-open-data/PHerc1218/volumes/"
              "20250521120456-8.640um-1.2m-116keV-masked.zarr")
    root = zarr.open(s3fs.S3Map(VOLUME, s3=s3fs.S3FileSystem(anon=True)), mode="r")

# ---- parámetros -------------------------------------------------------
Z_FROM_MM, Z_TO_MM = 120.0, 124.0            # zona recta
CENTER_MM, CENTER_Z_MM = (34.0, 38.5), 105.0  # tu ombligo a 105 mm (punto de partida de la búsqueda)
REACH_MM = 13.0                              # hasta dónde mirar desde el ombligo, a cada lado
BAND_MM = 0.05                               # grosor del corte (se promedia a través, muy fino)
TILE_MM, TILE_H_MM = 2.0, 2.0                # ventanas cuadradas de 2 x 2 mm (para seguir cada hoja en altura)
SHEET_MM = 0.17                              # regla: una hoja según nuestra medida
PERIOD_MM = (0.12, 0.25)                     # solo para el contador automático
SEARCH_MM = 4.0
L2, L1, L0 = root["2"], root["1"], root["0"]
P2, P1, P0 = 0.00864 * 4, 0.00864 * 2, 0.00864
t0c = time.time()
say = lambda m: print(f"[{time.time()-t0c:4.0f} s] {m}")

def slice2(z_mm):
    return np.asarray(L2[int(round(z_mm / P2)), :, :]).astype(np.float32)


def centre_axis(img):
    y, x = np.nonzero(img > 0)
    cx, cy = x.mean(), y.mean()
    dx, dy = x - cx, y - cy
    ang = 0.5 * np.arctan2(2 * (dx * dy).mean(), (dx * dx).mean() - (dy * dy).mean())
    return cx, cy, ang                          # ang = dirección de las alas




def bandpass(x, px):
    """deja solo ondas del tamaño de una hoja."""
    n = len(x)
    f = np.fft.rfftfreq(n, px)                  # ciclos por mm
    lo, hi = 1 / PERIOD_MM[1], 1 / PERIOD_MM[0]
    w = np.zeros_like(f)
    edge = 0.6
    core = (f >= lo) & (f <= hi)
    w[core] = 1
    rise = (f > lo - edge) & (f < lo); w[rise] = 0.5 - 0.5 * np.cos(np.pi * (f[rise] - lo + edge) / edge)
    fall = (f > hi) & (f < hi + edge); w[fall] = 0.5 + 0.5 * np.cos(np.pi * (f[fall] - hi) / edge)
    return np.fft.irfft(np.fft.rfft(x - x.mean()) * w, n)


def count_waves(prof, px):
    """cuenta ondas del tamaño de una hoja. Devuelve (cuenta, posiciones, separación mediana)."""
    x = prof - ndi.uniform_filter1d(prof, max(3, int(0.5 / px)))
    xb = bandpass(x, px)
    an = hilbert(xb)
    amp = np.abs(an); ph = np.unwrap(np.angle(an))
    f = np.gradient(ph) / (2 * np.pi) / px          # ondas por mm
    fmin, fmax = 1 / PERIOD_MM[1], 1 / PERIOD_MM[0]
    good = (amp > 0.35 * np.median(amp)) & (f > fmin) & (f < fmax)
    if good.sum() < 10:
        return np.nan, np.array([]), np.nan
    idx = np.arange(len(f))
    ff = np.where(good, f, np.interp(idx, idx[good], f[good]))   # huecos: ritmo de las hojas vecinas
    cum = np.cumsum(ff) * px
    pos = np.searchsorted(cum, np.arange(1, int(cum[-1]) + 1)) * px
    return float(cum[-1]), pos, float(1 / np.median(ff))


def disk(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return (xx**2 + yy**2) <= r * r


def find_core(z_mm, guess_mm):
    """busca el ombligo real cerca de la estimación: gravilla (mancha brillante granulada)
    y/o canal de aire. Devuelve (centro_mm, máscara, recuadro, método)."""
    R = int(5.0 / P1)
    gx, gy = int(guess_mm[0] / P1), int(guess_mm[1] / P1)
    y0, x0 = max(gy - R, 0), max(gx - R, 0)
    W = np.asarray(L1[int(round(z_mm / P1)), y0:gy + R, x0:gx + R]).astype(np.float32)
    v = W[W > 0]
    hv = v[v > np.percentile(v, 30)]                     # la parte "papel" (sin los huecos)
    med = np.median(hv)
    mad = 1.4826 * np.median(np.abs(hv[::5] - med))
    yy, xx = np.indices(W.shape)
    d = np.hypot(xx + x0 - gx, yy + y0 - gy) * P1
    near = d < SEARCH_MM
    # gravilla = textura granulada: mucho más rugosa que las hojas (medido: ~1,8 veces)
    w = max(3, int(0.1 / P1))
    m1 = ndi.uniform_filter(W, w); m2 = ndi.uniform_filter(W * W, w)
    rough = np.sqrt(np.clip(m2 - m1 * m1, 0, None))
    rref = np.median(rough[(W > 0) & near])
    grav = ndi.binary_opening((rough > 1.5 * rref) & near, disk(max(1, int(0.06 / P1))))
    grav = ndi.binary_fill_holes(ndi.binary_closing(grav, disk(int(0.15 / P1))))
    airm = ndi.binary_opening((W > 0) & (W < np.percentile(v, 8)) & near, disk(int(0.08 / P1)))
    best, how = None, "no encontrado (uso tu punto)"
    for mask, name, amin, test in ((grav, "gravilla", 0.2, True), (airm, "canal de aire", 0.1, False)):
        lab, n = ndi.label(mask)
        if not n:
            continue
        idx = np.arange(1, n + 1)
        sz = ndi.sum(np.ones_like(lab), lab, idx) * P1**2
        ok = sz >= amin
        if test:   # y además tiene granos brillantes: su parte más brillante destaca sobre el papel
            p90 = ndi.labeled_comprehension(W, lab, idx, lambda a: np.percentile(a, 90), float, 0)
            ok &= p90 >= med + 2 * mad
        if not ok.any():
            continue
        cy_, cx_ = np.array(ndi.center_of_mass(np.ones_like(lab), lab, idx[ok])).T
        dist = np.hypot(cx_ + x0 - gx, cy_ + y0 - gy)
        k = idx[ok][np.argmin(dist)]
        best, how = lab == k, name
        break
    if best is None:
        return np.array(guess_mm), np.zeros_like(W, bool), (y0, x0), how, W
    # juntar el aire pegado a la gravilla (es el mismo canal)
    if how == "gravilla":
        lab, n = ndi.label(airm)
        touch = np.unique(lab[ndi.binary_dilation(best, disk(int(0.2 / P1))) & (lab > 0)])
        best = best | np.isin(lab, touch[touch > 0])
    cy_, cx_ = ndi.center_of_mass(best)
    return np.array([(cx_ + x0) * P1, (cy_ + y0) * P1]), best, (y0, x0), how, W



# ---- 1. ombligo y eje corto a media altura -------------------------------
ZM = 0.5 * (Z_FROM_MM + Z_TO_MM)
ref = slice2(CENTER_Z_MM); rcx, rcy, _ = centre_axis(ref)
offx, offy = CENTER_MM[0] / P2 - rcx, CENTER_MM[1] / P2 - rcy; del ref
img2 = slice2(ZM); cx2, cy2, ang = centre_axis(img2); del img2
guess = np.array([cx2 + offx, cy2 + offy]) * P2
core, cmask, _, how, _ = find_core(ZM, guess)
say(f"ombligo a {ZM:.0f} mm encontrado por {how} ({np.hypot(*(core-guess)):.1f} mm de tu punto trasladado)")
u = np.array([-np.sin(ang), np.cos(ang)])
if u[1] > 0: u = -u                                    # u = hacia ARRIBA en la rodaja

# ---- 2. leer solo el bloque fino que contiene el corte ---------------------
ends = np.array([core + REACH_MM * u, core - REACH_MM * u])
pad = BAND_MM + 0.2
x0 = int((ends[:, 0].min() - pad) / P0); x1 = int((ends[:, 0].max() + pad) / P0) + 1
y0 = int((ends[:, 1].min() - pad) / P0); y1 = int((ends[:, 1].max() + pad) / P0) + 1
z0, z1 = int(Z_FROM_MM / P0), int(Z_TO_MM / P0)
x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, L0.shape[2]), min(y1, L0.shape[1])
say(f"leyendo bloque fino {z1-z0} x {y1-y0} x {x1-x0} píxeles ...")
B = np.asarray(L0[z0:z1, y0:y1, x0:x1])
say(f"bloque leído ({B.nbytes/1e6:.0f} MB)")

# ---- 3. el corte: filas = altura, columnas = distancia al ombligo ----------
v = np.array([u[1], -u[0]])                            # perpendicular, dentro de la rodaja
tt = np.arange(-REACH_MM, REACH_MM, P0)
ww = np.arange(-BAND_MM / 2, BAND_MM / 2 + 1e-9, P0)
P = core[None, None, :] + tt[:, None, None] * u + ww[None, :, None] * v
cols = P[..., 0] / P0 - x0; rows = P[..., 1] / P0 - y0
CUT = np.zeros((z1 - z0, tt.size), np.float32)
for i in range(z1 - z0):
    CUT[i] = ndi.map_coordinates(B[i].astype(np.float32), [rows, cols], order=1, cval=0).mean(1)
del B
say("corte hecho")

def edge(side):
    """distancia al último papel en ese sentido."""
    prof = CUT.mean(0); nz = prof[prof > 0]
    thr = np.percentile(nz, 20) if nz.size else 0
    idx = np.where(tt > 0)[0] if side > 0 else np.where(tt < 0)[0][::-1]
    inside = idx[ndi.uniform_filter1d((prof[idx] > thr).astype(float), int(0.3 / P0)) > 0.5]
    return abs(tt[inside[-1]]) + 0.2 if inside.size else REACH_MM

auto = {}
for side, name in ((1, "ARRIBA"), (-1, "ABAJO")):
    L = min(edge(side), REACH_MM)
    sel = (tt * side >= 0) & (tt * side <= L)
    D = CUT[:, sel] if side > 0 else CUT[:, sel][:, ::-1]           # columnas: 0 = ombligo
    dist = np.arange(D.shape[1]) * P0
    hmid = D.shape[0] // 2; hh = int(TILE_H_MM / P0 / 2)
    Dw = D[max(hmid - hh, 0):hmid + hh]
    lo, hi = np.percentile(Dw[Dw > 0], [1, 99.5]) if (Dw > 0).any() else (0, 1)
    nrow = int(np.ceil(L / TILE_MM))
    fig, axs = plt.subplots(nrow, 1, figsize=(11, 11.5 * nrow))
    axs = np.atleast_1d(axs)
    for r, ax in enumerate(axs):
        a0, a1 = r * TILE_MM, min((r + 1) * TILE_MM, L)
        c0, c1 = int(a0 / P0), int(a1 / P0)
        ax.imshow(Dw[:, c0:c1], cmap="gray", vmin=lo, vmax=hi, aspect="equal",
                  extent=[a0, a1, TILE_H_MM, 0], interpolation="nearest")
        ax.set_xlim(a0, a0 + TILE_MM)
        ax.set_xticks(np.arange(a0, a0 + TILE_MM + 1e-6, 0.5))
        ax.set_xticks(np.arange(a0, a0 + TILE_MM + 1e-6, 0.1), minor=True)
        ax.tick_params(which="minor", length=4); ax.tick_params(which="major", length=9)
        ax.set_yticks([])
        ax.plot([a0 + 0.05, a0 + 0.05 + SHEET_MM], [TILE_H_MM - 0.1] * 2, "r-", lw=4)
        ax.text(a0 + 0.05, TILE_H_MM - 0.18, "0,17 mm", color="r", fontsize=9)
    axs[0].set_title(f"corte vertical fino, eje corto, hacia {name}, alturas "
                     f"{Z_FROM_MM:.0f}-{Z_TO_MM:.0f} mm (se ven {TILE_H_MM} mm de alto). "
                     f"Distancia desde el ombligo en mm. Cuenta los HUECOS oscuros que atraviesan de arriba abajo (aire entre hojas).", fontsize=9)
    axs[-1].set_xlabel("mm desde el ombligo")
    plt.tight_layout()
    fn = f"{OUT}/corte_fino_{name.lower()}.png"
    plt.savefig(fn, dpi=150); plt.show()
    # a tamaño real, sin ejes, para ampliar
    plt.imsave(f"{OUT}/corte_fino_{name.lower()}_tamano_real.png",
               np.clip((Dw - lo) / (hi - lo), 0, 1), cmap="gray")
    n, _, sp = count_waves(D.mean(0)[int(0.3 / P0):], P0)
    auto[name] = (n, sp, L)
    say(f"hacia {name}: pared de {L:.1f} mm; figura guardada")

print("\n" + "=" * 66)
print("PRIMERO CUENTA TÚ en las figuras (rayas verticales = hojas).")
print("El contador automático NO decide esta pregunta: solo busca ondas de 0,12-0,25 mm,")
print("así que si las hojas midieran 0,3 mm contaría sus dos capas de fibra y daría el doble")
print("(probado en el banco: 30 hojas de 0,3 mm -> dice ~60). Solo como referencia:")
for name, (n, sp, L) in auto.items():
    print(f"  hacia {name}: {n:.0f} ondas de tamaño de hoja en {L:.1f} mm "
          f"(una cada {sp*1000:.0f} micras)")
print("Si cuentas unas 30 por lado: las hojas miden ~0,3 mm y hay que revisar las 55 vueltas.")
print("Si cuentas unas 50 por lado: lo que viste en el corte grueso eran paquetes.")
print("=" * 66)
json.dump(dict(core_mm=core.tolist(), how=how, auto={k: [float(x) for x in v_] for k, v_ in auto.items()}),
          open(f"{OUT}/corte_fino.json", "w"), indent=1)
print(f"Guardado en {OUT}")
print("listo")

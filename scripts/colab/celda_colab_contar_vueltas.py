# =====================================================================
# CELDA "CONTAR VUELTAS" — PHerc1218, zona recta
# Cuenta las hojas que cruza un camino recto desde el ombligo hasta el
# borde, por el eje corto (donde las hojas van planas y no hay pliegues),
# hacia ARRIBA y hacia ABAJO, en 4 alturas de la zona recta.
# Cada vuelta se cruza una vez arriba y una vez abajo: las dos cuentas
# deben coincidir.
#
# Cómo cuenta: mira el camino como una onda (hoja clara, hueco oscuro) y
# cuenta cuántas ondas hay, solo con ondas del tamaño de una hoja
# (0,12 a 0,25 mm). Así las dos capas de fibra de una misma hoja
# (unos 0,08 mm) no cuentan doble, y una hoja pegada a su vecina sin
# hueco sigue contando porque el ritmo se mantiene.
# Hace 5 caminos paralelos (separados 1 mm) en cada lado para ver si
# la cuenta es estable.
#
# NUEVO (23 sep): el ombligo se BUSCA en cada altura (la gravilla o el canal
# de aire lo marcan), porque el centro se tuerce en S y tu punto de 105 mm
# ya no vale a 130 mm. Los caminos salen del ombligo encontrado.
# El ombligo no se cuenta: se salta y se da aparte una estimación de
# cuántas vueltas esconde. Se da también la MEDIA de arriba y abajo, que
# no depende de dónde se ponga el centro.
#
# Veredicto fijado antes de correr (ver PASO 3).
# Autónoma: pegar entera en Colab. ~5-15 min.
# Guarda en Drive/vesuvius_1218/contar_vueltas/
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
from scipy.signal import hilbert, find_peaks

try:
    from google.colab import drive
    drive.mount("/content/drive")
    OUT = "/content/drive/MyDrive/vesuvius_1218/contar_vueltas"
except Exception:
    OUT = "./vesuvius_1218/contar_vueltas"
os.makedirs(OUT, exist_ok=True)

if "root" not in dir():
    VOLUME = ("vesuvius-challenge-open-data/PHerc1218/volumes/"
              "20250521120456-8.640um-1.2m-116keV-masked.zarr")
    root = zarr.open(s3fs.S3Map(VOLUME, s3=s3fs.S3FileSystem(anon=True)), mode="r")

# ---- parámetros -------------------------------------------------------
HEIGHTS_MM = [110.0, 120.0, 130.0, 140.0]     # zona recta, sin gravilla gorda
CENTER_MM, CENTER_Z_MM = (34.0, 38.5), 105.0  # ombligo de Diego (validado 22 sep)
OFFSETS_MM = [-2.0, -1.0, 0.0, 1.0, 2.0]      # caminos paralelos
BAND_MM = 0.3                                 # ancho que se promedia a lo largo de la hoja
PERIOD_MM = (0.12, 0.25)                      # tamaño de una hoja con su hueco
CORE_MAX_MM = 4.0                             # hasta dónde puede llegar el ombligo
L2, L1, L0 = root["2"], root["1"], root["0"]
P1 = 0.00864 * 2
SEARCH_MM = 4.0                               # radio de búsqueda del ombligo real
P2, P0 = 0.00864 * 4, 0.00864
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


ref = slice2(CENTER_Z_MM)
rcx, rcy, _ = centre_axis(ref)
offx, offy = CENTER_MM[0] / P2 - rcx, CENTER_MM[1] / P2 - rcy
del ref
say("ombligo de referencia listo")


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


cores = {}
results, strips = [], {}
for z in HEIGHTS_MM:
    img2 = slice2(z)
    cx2, cy2, ang = centre_axis(img2)
    guess = np.array([cx2 + offx, cy2 + offy]) * P2         # tu punto trasladado (mm)
    core, cmask, (cy0, cx0), how, Wc = find_core(z, guess)
    cores[z] = dict(guess=guess, core=core, mask=cmask, y0=cy0, x0=cx0, how=how, W=Wc)
    say(f"altura {z:.0f} mm: ombligo por {how}, a {np.hypot(*(core-guess)):.1f} mm de tu punto trasladado")
    v = np.array([np.cos(ang), np.sin(ang)])                  # a lo largo de las alas
    u = np.array([-np.sin(ang), np.cos(ang)])                 # eje corto
    if u[1] > 0:
        u = -u                                                # u apunta hacia ARRIBA en la imagen
    mask2 = img2 > 0
    # hasta dónde llega el rollo en cada sentido (en la vista gruesa)
    lens = {}
    for side, sgn in (("ARRIBA", 1), ("ABAJO", -1)):
        tt = np.arange(0, 40, P2)
        pts = core[None, :] + sgn * tt[:, None] * u[None, :]
        ix = np.clip((pts[:, 0] / P2).astype(int), 0, img2.shape[1] - 1)
        iy = np.clip((pts[:, 1] / P2).astype(int), 0, img2.shape[0] - 1)
        inside = mask2[iy, ix]
        last = np.where(inside)[0]
        lens[side] = tt[last.max()] + 0.5 if last.size else 0
    del img2
    # recuadro fino que contiene todos los caminos
    Lmax = max(lens.values())
    corners = []
    for sgn in (1, -1):
        for o in (min(OFFSETS_MM) - BAND_MM, max(OFFSETS_MM) + BAND_MM):
            for t in (0, Lmax):
                corners.append(core + sgn * t * u + o * v)
    corners = np.array(corners) / P0
    x0, y0 = np.floor(corners.min(0)).astype(int) - 8
    x1, y1 = np.ceil(corners.max(0)).astype(int) + 8
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, L0.shape[2]), min(y1, L0.shape[1])
    B = np.asarray(L0[int(round(z / P0)), y0:y1, x0:x1]).astype(np.float32)
    say(f"altura {z:.0f} mm: recuadro fino {B.shape} leído")
    nz = B[B > 0]
    air = np.percentile(nz, 5); pap = np.percentile(nz, 60)
    for side, sgn in (("ARRIBA", 1), ("ABAJO", -1)):
        tt = np.arange(0, lens[side], P0)
        ww = np.arange(-BAND_MM / 2, BAND_MM / 2 + 1e-9, P0)
        for o in OFFSETS_MM:
            P = core[None, None, :] + sgn * tt[:, None, None] * u + (o + ww)[None, :, None] * v
            cols = P[..., 0] / P0 - x0; rows = P[..., 1] / P0 - y0
            S = ndi.map_coordinates(B, [rows, cols], order=1, cval=0)   # (t, ancho)
            prof = S.mean(1)
            sm = ndi.uniform_filter1d(prof, int(0.1 / P0))
            sm3 = ndi.uniform_filter1d(prof, int(0.3 / P0))
            # ombligo: saltar el canal (aire o gravilla) hasta papiro normal sostenido 0,3 mm
            ok = (sm > air + 0.35 * (pap - air)) & (sm < pap * 1.12)
            run = ndi.uniform_filter1d(ok.astype(float), int(0.3 / P0)) > 0.95
            # además, el papiro tiene RITMO de hojas; el ombligo (polvo, gravilla) no
            xb = bandpass(prof - ndi.uniform_filter1d(prof, int(0.5 / P0)), P0)
            env = ndi.uniform_filter1d(np.abs(hilbert(xb)), int(0.3 / P0))
            # borde: último punto con materia
            inside = np.where(sm3 > air + 0.5 * (pap - air))[0]
            i1 = int(inside.max()) if inside.size else len(prof) - 1
            ref_env = np.median(env[int(0.3 * i1):i1]) if i1 > 10 else np.median(env)
            rhythm = ndi.uniform_filter1d((env > 0.5 * ref_env).astype(float), int(0.3 / P0)) > 0.95
            lim = int(CORE_MAX_MM / P0)
            both = run & rhythm
            i0 = int(np.argmax(both[:lim])) if both[:lim].any() else 0
            # si el camino pisa la máscara del ombligo encontrado, saltarla entera
            mc = cores[z]["mask"]
            if mc.any():
                pts = core[None, :] + sgn * tt[:lim, None] * u + o * v
                mi = np.round(pts[:, 1] / P1 - cores[z]["y0"]).astype(int)
                mj = np.round(pts[:, 0] / P1 - cores[z]["x0"]).astype(int)
                okk = (mi >= 0) & (mj >= 0) & (mi < mc.shape[0]) & (mj < mc.shape[1])
                hit = np.zeros(len(pts), bool); hit[okk] = mc[mi[okk], mj[okk]]
                if hit.any():
                    i0 = max(i0, int(np.where(hit)[0].max()) + int(0.1 / P0))
            n, pos, sp = count_waves(prof[i0:i1 + 1], P0)
            results.append(dict(z=z, lado=side, offset=o, vueltas=n, sep_mm=sp,
                                omb_mm=i0 * P0, pared_mm=(i1 - i0) * P0))
            if o == 0.0:
                strips[(z, side)] = (S, i0, i1, pos + i0 * P0)
    del B

# ---- PASO 1: tabla -----------------------------------------------------
import collections
print("\n" + "=" * 66)
print("CUENTA DE VUELTAS (5 caminos paralelos por lado; mediana y rango)")
best = []
summary = collections.OrderedDict()
for z in HEIGHTS_MM:
    row = {}
    for side in ("ARRIBA", "ABAJO"):
        r = [d for d in results if d["z"] == z and d["lado"] == side]
        c = np.array([d["vueltas"] for d in r], float)
        row[side] = (np.nanmedian(c), np.nanmin(c), np.nanmax(c),
                     np.nanmedian([d["sep_mm"] for d in r]), np.nanmedian([d["omb_mm"] for d in r]))
    summary[z] = row
    a, b = row["ARRIBA"], row["ABAJO"]
    agree = abs(a[0] - b[0]) <= 3
    print(f"altura {z:.0f} mm | arriba {a[0]:5.1f} ({a[1]:.0f}-{a[2]:.0f}) | "
          f"abajo {b[0]:5.1f} ({b[1]:.0f}-{b[2]:.0f}) | media {0.5*(a[0]+b[0]):5.1f} | "
          f"{'COINCIDEN' if agree else 'NO coinciden'}")
    if agree:
        best.append(0.5 * (a[0] + b[0]))

# ---- PASO 2: vueltas escondidas en el ombligo ---------------------------
omb = np.nanmedian([d["omb_mm"] for d in results])
sep = np.nanmedian([d["sep_mm"] for d in results])
hid = omb / sep if sep > 0 else np.nan
print(f"\nombligo saltado: {omb:.2f} mm a cada lado; separación entre hojas {sep*1000:.0f} µm")
print(f"-> vueltas que podría esconder el ombligo: unas {hid:.0f} (estimación, no cuenta)")

# ---- PASO 3: veredicto (fijado antes de correr) -------------------------
print("\n" + "=" * 66)
if best:
    nb = max(best)
    print(f"VEREDICTO: {nb:.0f} vueltas contadas fuera del ombligo "
          f"(la altura más completa de las que coinciden arriba y abajo)")
    print(f"           + unas {hid:.0f} escondidas en el ombligo (estimadas)")
    print(f"           = unas {nb + hid:.0f} vueltas en total")
    spread = [summary[z]["ARRIBA"][2] - summary[z]["ARRIBA"][1] for z in HEIGHTS_MM]
    if np.nanmax(spread) > 8:
        print("AVISO: los caminos paralelos difieren mucho en alguna altura; mira las tiras.")
else:
    print("VEREDICTO: SIN ACUERDO — en ninguna altura coinciden arriba y abajo. "
          "Hay que mirar las tiras a ojo antes de dar un número.")
    means = [0.5 * (summary[z]["ARRIBA"][0] + summary[z]["ABAJO"][0]) for z in HEIGHTS_MM]
    print(f"  (dato aparte, no veredicto: la media arriba/abajo va de {min(means):.0f} a {max(means):.0f})")
print("=" * 66)
json.dump(dict(results=results, veredicto=(max(best) if best else None),
               ombligo_vueltas=hid), open(f"{OUT}/contar_vueltas.json", "w"), indent=1,
          default=float)

# ---- comprobación: dónde se encontró el ombligo -------------------------
fig, axs = plt.subplots(1, len(cores), figsize=(5 * len(cores), 5))
for ax, (z, c) in zip(np.atleast_1d(axs), cores.items()):
    W = c["W"]; vv = W[W > 0]
    ext = [c["x0"] * P1, (c["x0"] + W.shape[1]) * P1, (c["y0"] + W.shape[0]) * P1, c["y0"] * P1]
    ax.imshow(W, cmap="gray", vmin=np.percentile(vv, 1), vmax=np.percentile(vv, 99.5), extent=ext)
    if c["mask"].any():
        ax.contour(np.linspace(ext[0], ext[1], W.shape[1]), np.linspace(ext[3], ext[2], W.shape[0]),
                   c["mask"], [0.5], colors="y", linewidths=1)
    ax.plot(*c["guess"], "w+", ms=16, mew=2); ax.plot(*c["core"], "g+", ms=16, mew=2)
    ax.set_title(f"{z:.0f} mm: blanca = tu punto trasladado;\nverde = ombligo encontrado ({c['how']})",
                 fontsize=9)
    ax.axis("off")
plt.tight_layout(); plt.savefig(f"{OUT}/ombligo_encontrado.png", dpi=130); plt.show()
print("MIRA: la cruz verde debe caer en el canal del ombligo (gravilla o aire), no en una grieta.")

# ---- figuras: resumen y tiras para contar a ojo -------------------------
fig, ax = plt.subplots(figsize=(8, 4))
for side, c in (("ARRIBA", "C0"), ("ABAJO", "C3")):
    for z in HEIGHTS_MM:
        vals = [d["vueltas"] for d in results if d["z"] == z and d["lado"] == side]
        ax.plot([z + (-0.8 if side == "ARRIBA" else 0.8)] * len(vals), vals, "o", color=c, alpha=0.6,
                label=side if z == HEIGHTS_MM[0] else None)
ax.set_xlabel("altura (mm)"); ax.set_ylabel("vueltas contadas")
ax.set_title("cada punto = un camino"); ax.legend()
plt.tight_layout(); plt.savefig(f"{OUT}/resumen.png", dpi=120); plt.show()

ROW_MM = 4.0
for (z, side), (S, i0, i1, pos) in strips.items():
    img = S.T                                                     # ancho x largo
    L = img.shape[1] * P0
    nrow = int(np.ceil(L / ROW_MM))
    v_ = img[img > 0]
    lo, hi = (np.percentile(v_, 1), np.percentile(v_, 99.5)) if v_.size else (0, 1)
    fig, axs = plt.subplots(nrow, 1, figsize=(16, 1.9 * nrow))
    axs = np.atleast_1d(axs)
    for r, ax in enumerate(axs):
        a0, a1 = r * ROW_MM, min((r + 1) * ROW_MM, L)
        c0, c1 = int(a0 / P0), int(a1 / P0)
        ax.imshow(img[:, c0:c1], cmap="gray", vmin=lo, vmax=hi, aspect="equal",
                  extent=[a0, a1, BAND_MM / 2, -BAND_MM / 2])
        pp = pos[(pos >= a0) & (pos < a1)]
        ax.plot(pp, np.full(pp.size, -BAND_MM / 2), "rv", ms=4)
        for t, cc in ((i0 * P0, "c"), (i1 * P0, "y")):
            if a0 <= t < a1:
                ax.axvline(t, color=cc, lw=2)
        ax.set_yticks([]); ax.set_xlim(a0, a0 + ROW_MM)
    axs[0].set_title(f"{z:.0f} mm, hacia {side}: triángulos rojos = hojas contadas; "
                     f"azul = fin del ombligo; amarillo = borde. Distancia en mm desde el ombligo")
    plt.tight_layout()
    plt.savefig(f"{OUT}/tira_{int(z)}_{side.lower()}.png", dpi=170)
    if z == 130.0:
        plt.show()
    else:
        plt.close()
print(f"Guardado en {OUT}: resumen.png, tira_<altura>_<lado>.png, contar_vueltas.json")
print("Las tiras de 130 mm salen aquí; las demás están en Drive para ampliar.")
print("listo")

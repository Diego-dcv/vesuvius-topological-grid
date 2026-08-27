# =====================================================================
# CELDA KOL-3 — kollesis por DENSIDAD: plegado del brillo sobre la hoja
#
# Motivación (pregunta de Diego): el alisado de las uniones servía a la
# cara del escriba; el verso conservaba escalón, y el bruñido COMPRIME
# en vez de quitar — fibra comprimida + engrudo = más densidad = más
# brillo en CT. Buscamos una raya vertical de brillo cada W fijo de mm.
#
# ORDEN tras (re)conexión: (1) celda de carga → (2) TEX-0 (vol) → (3) esta.
# ~10 min con Z_STRIDE=2.
#
# CRITERIOS PREFIJADOS (antes de mirar):
#  - perfil: b(L) = mediana en z del brillo muestreado en la posición real
#    de cada cruce (máx r±2 px), bins de 2 mm, SIN los rayos θ∈{354..6}°
#    (juntura instrumental, excluida por declaración), dominio L<4,10 m,
#    columnas con ≥30 filas z cubiertas; e(L) = b / base móvil ±50 mm
#  - plegado: barrido W = 120..260 mm en dos etapas (paso 1 mm y refinado
#    a 0,1 mm en los 3 mejores — con ~20 períodos en 4 m, 1 mm de error en
#    W desfasa el apilado); 30 bins de fase, SNR sobre medianas
#  - significación GLOBAL: 500 permutaciones de BLOQUES de 40 mm (rompen
#    la periodicidad, conservan la autocorrelación corta; el desplazamiento
#    circular NO vale — un banco lo cazó: rodar un perfil periódico lo deja
#    periódico). Una periodicidad POR VUELTA no pliega coherente a W fijo:
#    su período crece con L — el discriminador del chirp.
#  - SUELO DE SENSIBILIDAD medido en banco: bandas de ~8 mm y ≥5% de
#    elevación se detectan (2/3 réplicas); +3% queda por debajo del suelo.
#    Un nulo aquí significa "no hay bandas periódicas ≥~5%", no "no hay".
#  - se busca PICO (unión = más densa); el mínimo se imprime igualmente
#  - VEREDICTO positivo solo si p<0,01 Y ancho del pico 5-30 mm Y
#    elevación ≥2%. Si no: NULO publicado (tercero del capítulo kollesis).
#
# Salidas: kol3_brillo_1218.npz, kol3_plegado.png
# =====================================================================
import numpy as np, matplotlib.pyplot as plt, csv, io, urllib.request
import warnings, time
warnings.filterwarnings("ignore", message="All-NaN")

t0 = time.time()
for v in ["rows", "zs", "zpos", "dz_mm", "vol"]:
    assert v in dir(), f"falta {v}: corre carga de tabla y TEX-0"
VOX = 0.01728; COB_MIN = 0.10
DX, DY = -3, -1
Z_STRIDE = 2
RAYOS_FUERA = {59, 0, 1}                    # θ 354°, 0°, 6°
rng = np.random.default_rng(31)
RAW = ("https://raw.githubusercontent.com/Jinhojeong/"
       "vesuvius-surface-geometry-diagnostic/main/results/kollesis/")

# orígenes (marco CT: con el offset (−3,−1), como DES-2)
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

# geometría L (idéntica a DES-1/DES-2)
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
seg = np.sqrt((rv * np.radians(6.0)) ** 2 + np.diff(rv, prepend=rv[0]) ** 2)
Lfin = np.cumsum(seg); Lc = Lfin - seg / 2

por_z = {}
for r in rows:
    k = int(r["k"])
    if not (K0 <= k <= K1):
        continue
    por_z.setdefault(int(r["z"]), []).append(
        (k, int(round(float(r["theta_deg"]) / 6)) % 60,
         float(r["r_l1_vox"])))

# muestreo del CT (como DES-2) con acumulador extra SIN la juntura
nbL = int(Lfin[-1] / 2.0)
SUM = np.zeros((nbL, nz), np.float32); CNT = np.zeros((nbL, nz), np.float32)
SUMf = np.zeros((nbL, nz), np.float32); CNTf = np.zeros((nbL, nz), np.float32)
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
    Lb = np.clip((Lc[(kk - K0) * 60 + ib] / (Lfin[-1] / nbL)).astype(int),
                 0, nbL - 1)
    iz = zpos[zv]
    np.add.at(SUM, (Lb, iz), val); np.add.at(CNT, (Lb, iz), 1)
    fuera = np.isin(ib, list(RAYOS_FUERA))
    np.add.at(SUMf, (Lb[~fuera], iz), val[~fuera])
    np.add.at(CNTf, (Lb[~fuera], iz), 1)
    if n_ % 40 == 0:
        print(f"  {n_}/{len(z_list)}  [{time.time()-t0:.0f}s]")
IMG = np.divide(SUM, CNT, out=np.full_like(SUM, np.nan), where=CNT > 0)
IMGf = np.divide(SUMf, CNTf, out=np.full_like(SUMf, np.nan), where=CNTf > 0)
np.savez_compressed("kol3_brillo_1218.npz", IMG=IMG, IMGf=IMGf,
                    L_mm=np.arange(nbL) * Lfin[-1] / nbL, dz_mm=dz_mm)
print(f"matriz de brillo guardada  [{time.time()-t0:.0f}s]")

# perfil e(L) y plegado
Lmm = (np.arange(nbL) + 0.5) * (Lfin[-1] / nbL)
cobz = np.isfinite(IMGf).sum(axis=1)
b = np.nanmedian(IMGf, axis=1)
m = (Lmm < 4100) & (cobz >= 30) & np.isfinite(b)
base = np.array([np.nanmedian(b[m & (np.abs(Lmm - L) <= 50)])
                 for L in Lmm])
E = np.where(m, b / base, np.nan)
print(f"perfil: {m.sum():,} bins de 2 mm cubiertos")

NB = 30
def hazfold(g, p, W):
    ph = ((g % W) / W * NB).astype(np.int64)
    bm = np.array([np.median(p[ph == b_]) if (ph == b_).any() else np.nan
                   for b_ in range(NB)])
    mad = 1.4826 * np.nanmedian(np.abs(bm - np.nanmedian(bm))) + 1e-9
    return (np.nanmax(bm) - np.nanmedian(bm)) / mad
def snr_max(perfil):
    fin = np.isfinite(perfil)
    g = Lmm[fin]; p = perfil[fin]
    Ws1 = np.arange(120.0, 260.5, 1.0)
    ss = np.array([hazfold(g, p, W) for W in Ws1])
    best, bw = -9, None
    for W0 in Ws1[np.argsort(ss)[-3:]]:            # refinado a 0,1 mm
        for W in np.arange(W0 - 1, W0 + 1.001, 0.1):
            s = hazfold(g, p, W)
            if s > best: best, bw = s, W
    return best, bw
def perm_bloques(perfil):
    B = 20                                          # 20 bins de 2 mm = 40 mm
    nb = len(perfil) // B
    idx = rng.permutation(nb)
    return np.concatenate([perfil[i_ * B:(i_ + 1) * B] for i_ in idx]
                          + [perfil[nb * B:]])

rms = np.nanstd(E)
print(f"ruido del perfil (rms de e): {rms*100:.1f}% — el suelo del banco "
      f"(≥5%) se midió a 3% de rms; escala en proporción")
obs, Wwin = snr_max(E)
print(f"observado: máx SNR {obs:.2f} en W = {Wwin:.1f} mm")
NMC = 500; peor = 0
for i in range(NMC):
    if snr_max(perm_bloques(E))[0] >= obs: peor += 1
    if (i + 1) % 100 == 0:
        print(f"  MC {i+1}/{NMC}  p̂ {peor/(i+1):.3f}  "
              f"[{time.time()-t0:.0f}s]")
p = peor / NMC
fin = np.isfinite(E)
ph = ((Lmm[fin] % Wwin) / Wwin * NB).astype(np.int64)
bm = np.array([np.median(E[fin][ph == b_]) for b_ in range(NB)])
elev = (np.max(bm) / np.median(bm) - 1) * 100
hond = (1 - np.min(bm) / np.median(bm)) * 100
anch = (bm > np.median(bm) + 0.5 * (np.max(bm) - np.median(bm))).sum() \
       * Wwin / NB
print(f"\np global = {p:.3f} | pico plegado W={Wwin:.0f} mm: "
      f"elevación {elev:.2f}%  ancho ~{anch:.0f} mm | "
      f"(mínimo, informativo: -{hond:.2f}%)")
positivo = p < 0.01 and 5 <= anch <= 30 and elev >= 2.0
print(f"VEREDICTO KOL-3: "
      f"{'CANDIDATO A POSITIVO — revisar antes de contarlo' if positivo else 'NULO'}")

fig, ax = plt.subplots(1, 2, figsize=(15, 4),
                       gridspec_kw={"width_ratios": [3, 1]})
ax[0].plot(Lmm[fin] / 1000, E[fin], ".", ms=2, alpha=0.4)
ax[0].set_xlabel("L (m)"); ax[0].set_ylabel("brillo relativo e(L)")
ax[0].set_title("perfil de brillo sobre la hoja (sin juntura instrumental)")
ax[1].plot(np.arange(NB) / NB * Wwin, bm, "o-")
ax[1].set_xlabel(f"fase (mm) — W = {Wwin:.0f} mm")
ax[1].set_title(f"plegado ganador  p={p:.3f}")
for A in ax: A.grid(alpha=0.3)
plt.tight_layout(); plt.savefig("kol3_plegado.png", dpi=130)
print(f"figuras y npz escritos  [{time.time()-t0:.0f}s]")

# planchado_1218.py: el examen de cuña, arreglado (la PL-1 tenía la máscara vacía)
# Fallo de la PL-1 (declarado): el detector de cuñas exigía cobertura <15%
# en el tercio exterior, pero las cuñas reales del 1218 rondan 20-35%
# (el censo es rampa, no acantilado) → máscara vacía → examen sobre CERO
# vueltas → nan, y el veredicto trató el nan como suspenso. Dos arreglos:
# umbral RELATIVO (bins bajo la mitad de la mediana angular) con reserva
# (los 20 bins más pobres), y guarda explícita "no corrió ≠ falló".
# Mejora pedida por el dato: ratio por PROFUNDIDAD (mitad interior vs
# exterior) — el interpolante se usará sobre todo fuera.
# Los criterios prefijados NO cambian.
# Pregunta: ¿el relieve es separable, Δr(vuelta,θ,z) ≈ A(vuelta) · F(θ,z)?
# Si lo es, F es el PATRÓN MAESTRO del plegado y la ley interpola las cuñas
# muertas del censo (predice dónde pasa la hoja donde la segmentación falla).
#
# PRE-VUELO de "no funciona" (declarado antes de mirar):
#  (a) si la fase del patrón deriva entre vueltas, la mediana compartida se
#      emborrona → ratio alto → la ley separable muere aquí (peldaño
#      siguiente sería alinear fase por vuelta; sesión aparte);
#  (b) F se estima sobre todo con las vueltas interiores (las cuñas mueren
#      desde k≈45); el examen de cuña mide exactamente ese traslado;
#  (c) la tabla es mediana a 6° → el residuo llevará estructura fina real.
#
# CRITERIOS PREFIJADOS (antes de correr):
#  - AUTOEXAMEN sintético (dentro de la celda): corr(F̂, F_verdad) ≥ 0,9 y
#    ratio de cuña ≤ 0,6 → el ajustador funciona; si falla, el resto NO corre.
#  - DATO REAL, examen de cuña (mediana del ratio RMSE/σ en celdas ocultas;
#    F ajustada SIN la vuelta examinada, A solo con sus cantos):
#      ≤ 0,7   → ley con palanca (el planchado interpola)
#      0,7-0,9 → ley débil (guía, no plancha)
#      > 0,9   → sin ley separable (negativo con derecho)
import numpy as np, matplotlib.pyplot as plt, warnings
warnings.filterwarnings("ignore", message="All-NaN")
warnings.filterwarnings("ignore", message="Mean of empty")
warnings.filterwarnings("ignore", message="Degrees of freedom")

VOX = 0.01728; COB_MIN = 0.10; MINK = 8

# ---------- 0) rejilla, censo y relieve (idéntico a IMG-5 v5) ----------
kmax = max(int(r["k"]) for r in rows)
nz = len(zs)
R = np.full((kmax + 1, 60, nz), np.nan, np.float32)
for r in rows:
    R[int(r["k"]),
      int(round(float(r["theta_deg"]) / 6)) % 60,
      zpos[int(r["z"])]] = float(r["r_l1_vox"]) * VOX
cob = np.isfinite(R).reshape(kmax + 1, -1).mean(axis=1)
K0 = 2
K1 = max(k for k in range(kmax + 1) if cob[k] >= COB_MIN)
Rv = R[K0:K1 + 1]; nk = K1 - K0 + 1
cob2d = np.isfinite(Rv).mean(axis=2)                 # (nk, 60)

rmed = np.nanmedian(Rv, axis=2)
rk = np.nanmedian(rmed, axis=1)
fin = np.isfinite(rk)
rk = np.interp(np.arange(nk), np.arange(nk)[fin], rk[fin])
for a in range(nk):
    fila = rmed[a]; fila[~np.isfinite(fila)] = rk[a]

W = 41; ker = np.ones(W, np.float32)
D = np.full_like(Rv, np.nan)
for a in range(nk):
    for i in range(60):
        y = Rv[a, i]; ok = np.isfinite(y)
        if ok.sum() < 30:
            continue
        num = np.convolve(np.pad(np.where(ok, y, 0).astype(np.float32),
                                 W // 2, mode="reflect"), ker, "valid")
        den = np.convolve(np.pad(ok.astype(np.float32),
                                 W // 2, mode="reflect"), ker, "valid")
        s = np.divide(num, den, out=np.full(nz, np.nan, np.float32),
                      where=den > 0)
        D[a, i] = np.where(ok, y - s, np.nan)

# ---------- herramientas del ajuste separable ----------
def escala_rob(x):
    med = np.nanmedian(x)
    return 1.4826 * np.nanmedian(np.abs(x - med))

def ajusta_F(Dm, usar):
    "F = mediana entre vueltas 'usar' del relieve normalizado por vuelta"
    N = []
    for a in usar:
        s = escala_rob(Dm[a])
        if np.isfinite(s) and s > 1e-6:
            N.append(Dm[a] / s)
    N = np.array(N)
    cnt = np.isfinite(N).sum(axis=0)
    return np.where(cnt >= MINK, np.nanmedian(N, axis=0), np.nan)

def amplitud(Dk, F, vis=None):
    "A de una vuelta por mínimos cuadrados sobre las celdas visibles"
    m = np.isfinite(Dk) & np.isfinite(F)
    if vis is not None:
        m &= vis
    if m.sum() < 200:
        return np.nan
    return float(np.sum(Dk[m] * F[m]) / np.sum(F[m] ** 2))

def examen_cuña(Dm, wtheta, tests):
    "por vuelta de test: F sin ella, A con sus cantos, predicción en la cuña"
    pares = []
    todas = list(range(Dm.shape[0]))
    vis = np.ones_like(Dm[0], bool); vis[wtheta, :] = False   # cantos
    for t in tests:
        F = ajusta_F(Dm, [a for a in todas if a != t])
        A = amplitud(Dm[t], F, vis=vis)
        if not np.isfinite(A):
            continue
        oculto = np.zeros_like(vis); oculto[wtheta, :] = True
        m = oculto & np.isfinite(Dm[t]) & np.isfinite(F)
        if m.sum() < 200:
            continue
        resid = Dm[t][m] - A * F[m]
        sig = np.std(Dm[t][m])
        if sig > 1e-6:
            pares.append((t, float(np.sqrt(np.mean(resid ** 2)) / sig)))
    return pares

# ---------- 1) AUTOEXAMEN sintético del ajustador ----------
rng = np.random.default_rng(0)
nzs = 200; zsyn = np.arange(nzs) * 0.55
th = np.arange(60) * 6.0
Ft = (np.sin(2 * np.pi * zsyn / 19.8)[None, :]
      * (1 + 0.5 * np.cos(np.radians(th)))[:, None]
      + 1.2 * np.exp(-((np.arange(60) - 30) ** 2) / 4.0)[:, None]
      * np.sin(2 * np.pi * zsyn / 9.9)[None, :])
Ds = np.empty((40, 60, nzs), np.float32)
for a in range(40):
    Ds[a] = (0.5 + 0.03 * a) * Ft + 0.4 * rng.standard_normal((60, nzs))
wsyn = np.r_[7:20, 42:55]                       # cuñas sintéticas
for a in range(25, 40):
    Ds[a][wsyn, :] = np.nan                     # exterior sin cuñas (censo)
Ds[rng.random(Ds.shape) < 0.2] = np.nan
F_hat = ajusta_F(Ds, list(range(40)))
m = np.isfinite(F_hat) & np.isfinite(Ft)
corrF = float(np.corrcoef(F_hat[m], Ft[m])[0, 1])
r_syn = [r for _, r in examen_cuña(Ds, wsyn, list(range(3, 24, 4)))]
med_syn = float(np.median(r_syn))
print(f"AUTOEXAMEN: corr(F̂,F_verdad) = {corrF:.3f} (criterio ≥0,90); "
      f"ratio de cuña = {med_syn:.2f} (criterio ≤0,60), n={len(r_syn)}")
if corrF < 0.90 or med_syn > 0.60:
    raise SystemExit("AUTOEXAMEN FALLIDO — el ajustador no está listo; "
                     "no se toca el dato real.")
print("AUTOEXAMEN PASS — el ajustador ve la ley donde la hay.\n")

# ---------- 2) DATO REAL: ajuste completo y examen de cuña ----------
# cuñas reales: bins θ casi muertos en el tercio exterior del censo
ext = cob2d[2 * nk // 3:]
perfil = ext.mean(axis=0)                        # cobertura media por θ, fuera
umbral = 0.5 * np.median(perfil)
wtheta = np.where(perfil < umbral)[0]
if len(wtheta) < 6:                              # reserva: los 20 más pobres
    wtheta = np.argsort(perfil)[:20]
    umbral = float(perfil[wtheta].max())
print(f"cobertura por θ en el tercio exterior: mediana "
      f"{np.median(perfil):.2f}, mínimo {perfil.min():.2f}; "
      f"umbral de cuña {umbral:.2f}")
print(f"cuñas del censo: {len(wtheta)} bins de 6° → "
      f"{sorted(int(6*w) for w in wtheta)}")

F = ajusta_F(D, list(range(nk)))
A = np.array([amplitud(D[a], F) for a in range(nk)])
R2 = np.full(nk, np.nan)
for a in range(nk):
    mm = np.isfinite(D[a]) & np.isfinite(F)
    if mm.sum() > 500 and np.isfinite(A[a]):
        res = D[a][mm] - A[a] * F[mm]
        v = np.var(D[a][mm])
        if v > 1e-9:
            R2[a] = 1 - np.var(res) / v
print(f"ajuste completo: R² mediano por vuelta = {np.nanmedian(R2):.2f} "
      f"(p25 {np.nanpercentile(R2,25):.2f}, p75 {np.nanpercentile(R2,75):.2f}); "
      f"A crece {np.nanmedian(A[:nk//3]):.2f} → {np.nanmedian(A[-nk//3:]):.2f} "
      f"mm (interior→exterior)")

tests = list(range(4, nk - 1, 2))
pares = examen_cuña(D, wtheta, tests)
if not pares:
    print("\nEXAMEN DE CUÑA: NO CORRIÓ (máscara o celdas insuficientes) — "
          "SIN veredicto; revisar la máscara antes de afirmar nada.")
    med_real = np.nan
else:
    r_real = [r for _, r in pares]
    med_real = float(np.median(r_real))
    ic = np.percentile(r_real, [25, 75])
    r_int = [r for t, r in pares if t < nk // 2]
    r_ext = [r for t, r in pares if t >= nk // 2]
    print(f"\nEXAMEN DE CUÑA REAL: ratio mediano = {med_real:.2f} "
          f"[p25 {ic[0]:.2f}, p75 {ic[1]:.2f}], "
          f"vueltas examinadas = {len(pares)}")
    print(f"  por profundidad: mitad interior {np.median(r_int):.2f} "
          f"(n={len(r_int)}) | mitad exterior {np.median(r_ext):.2f} "
          f"(n={len(r_ext)})  ← el número del caso de uso")
    if med_real <= 0.70:
        print("VEREDICTO (criterio prefijado): LEY CON PALANCA — el "
              "planchado interpola las cuñas muertas.")
    elif med_real <= 0.90:
        print("VEREDICTO (criterio prefijado): ley DÉBIL — guía, no plancha.")
    else:
        print("VEREDICTO (criterio prefijado): SIN ley separable — negativo "
              "con derecho.")

# ---------- 3) figuras ----------
# 3a) el patrón maestro F(θ,z)
plt.figure(figsize=(14, 4))
vF = np.nanpercentile(np.abs(F), 95)
plt.imshow(F.T, aspect="auto", origin="lower", cmap="RdBu_r",
           vmin=-vF, vmax=vF, extent=[0, 360, 0, nz * dz_mm])
plt.colorbar(label="F (relieve normalizado)", pad=0.01)
plt.xlabel("θ (°)"); plt.ylabel("altura (mm)")
plt.title("PHerc1218 — el patrón maestro del plegado F(θ, z): "
          "la arruga que todas las vueltas comparten")
plt.tight_layout()
plt.savefig("campo_pliegues_1218.png", dpi=150, bbox_inches="tight")
plt.show()

# 3b) amplitud y R² por vuelta
fig, ax1 = plt.subplots(figsize=(10, 3.5))
ax1.plot(np.arange(K0, K1 + 1), A, "o-", ms=3, color="tab:red",
         label="A(k) [mm]")
ax1.set_xlabel("vuelta k"); ax1.set_ylabel("A (mm)", color="tab:red")
ax2 = ax1.twinx()
ax2.plot(np.arange(K0, K1 + 1), R2, "s-", ms=3, color="tab:blue",
         alpha=0.6, label="R²(k)")
ax2.set_ylabel("R²", color="tab:blue"); ax2.set_ylim(0, 1)
plt.title("amplitud del plegado y varianza explicada, por vuelta")
plt.tight_layout()
plt.savefig("amplitud_planchado_1218.png", dpi=150, bbox_inches="tight")
plt.show()

# 3c) el planchado: la cinta antes / después (mismo pintado que la v5)
def rellena(col, gmax=4):
    ok = np.isfinite(col)
    if ok.sum() < 2:
        return col
    idx = np.arange(len(col)); pos = idx[ok]
    lleno = np.interp(idx, pos, col[ok])
    j = np.searchsorted(pos, idx)
    j0 = np.clip(j - 1, 0, len(pos) - 1); j1 = np.clip(j, 0, len(pos) - 1)
    dist = np.minimum(np.abs(idx - pos[j0]), np.abs(idx - pos[j1]))
    return np.where(dist <= gmax, lleno, np.nan)

RES = D - A[:, None, None] * F[None, :, :]        # el residuo tras planchar
rv = rmed.ravel(); drv = np.diff(rv, prepend=rv[0])
seg = np.sqrt((rv * np.radians(6.0)) ** 2 + drv ** 2)
Lfin = np.cumsum(seg); Lini = Lfin - seg; Lmax = Lfin[-1]
paso = 0.5; ncol = int(np.ceil(Lmax / paso))

def pinta(M):
    ACC = np.zeros((nz, ncol), np.float32); CNT = np.zeros_like(ACC)
    for a in range(nk):
        for i in range(60):
            j = a * 60 + i
            col = rellena(M[a, i]); f = np.isfinite(col)
            if not f.any():
                continue
            c0 = int(Lini[j] / paso)
            c1 = min(max(c0 + 1, int(np.ceil(Lfin[j] / paso))), ncol)
            if c1 > c0:
                ACC[f, c0:c1] += col[f, None]; CNT[f, c0:c1] += 1
    return np.divide(ACC, CNT, out=np.full_like(ACC, np.nan), where=CNT > 0)

IMG0, IMG1 = pinta(D), pinta(RES)
v = np.nanpercentile(np.abs(IMG0), 95)
fig, axs = plt.subplots(2, 1, figsize=(22, 8), sharex=True)
for ax, M, t in [(axs[0], IMG0, "antes: relieve medido"),
                 (axs[1], IMG1, "después: residuo tras quitar A(k)·F(θ,z) "
                                "— lo que la plancha no explica")]:
    im = ax.imshow(M, aspect="auto", origin="lower", cmap="RdBu_r",
                   vmin=-v, vmax=v, extent=[0, Lmax / 1000, 0, nz * dz_mm])
    ax.set_ylabel("altura (mm)"); ax.set_title(t, fontsize=11)
fig.colorbar(im, ax=axs, label="relieve radial (mm)", pad=0.01)
axs[1].set_xlabel("desarrollo del papiro (m)")
plt.savefig("planchado_antes_despues_1218.png", dpi=150,
            bbox_inches="tight")
plt.show()
s0 = np.nanstd(IMG0); s1 = np.nanstd(IMG1)
print(f"\nguardadas 3 figuras — relieve global: ±{s0:.2f} mm antes, "
      f"±{s1:.2f} mm después ({100*(1-s1/s0):.0f}% planchado)")
import numpy as np, matplotlib.pyplot as plt, warnings
from matplotlib import gridspec
warnings.filterwarnings("ignore", message="All-NaN")

VOX = 0.01728          # mm/vóxel en L1
COB_MIN = 0.10         # cobertura mínima por vuelta para entrar en la cinta
GAP_Z = 4              # hueco máximo en z que se rellena (muestras; ~2,2 mm)

# --- 1) la tabla completa a rejilla (vuelta, θ, z)
kmax = max(int(r["k"]) for r in rows)
nz = len(zs)
R = np.full((kmax + 1, 60, nz), np.nan, np.float32)
for r in rows:
    R[int(r["k"]),
      int(round(float(r["theta_deg"]) / 6)) % 60,
      zpos[int(r["z"])]] = float(r["r_l1_vox"]) * VOX

# --- 2) censo de cobertura por vuelta
cob = np.isfinite(R).reshape(kmax + 1, -1).mean(axis=1)
print("censo de cobertura por vuelta (% de celdas θ×z con dato):")
for c in range(0, kmax + 1, 12):
    print("  " + "  ".join(f"k{k:02d}:{100*cob[k]:3.0f}"
                           for k in range(c, min(c + 12, kmax + 1))))
K0 = 2
K1 = max(k for k in range(kmax + 1) if cob[k] >= COB_MIN)
print(f"\nvueltas que entran: {K0}..{K1} (la tabla llega a {kmax})")

ks = np.arange(K0, K1 + 1); nk = len(ks)
Rv = R[K0:K1 + 1]
cob2d = np.isfinite(Rv).mean(axis=2)               # (nk, 60): mapa vuelta×θ

# --- 3) radio mediano por (vuelta, θ); huecos por interpolación en k
rmed = np.nanmedian(Rv, axis=2)
rk = np.nanmedian(rmed, axis=1)
f = np.isfinite(rk)
rk = np.interp(np.arange(nk), np.arange(nk)[f], rk[f])
for a in range(nk):
    fila = rmed[a]
    fila[~np.isfinite(fila)] = rk[a]
print(f"radio mediano: {rk[0]:.2f} mm (vuelta {K0}) → "
      f"{rk[-1]:.2f} mm (vuelta {K1})")

# --- 4) relieve: radio − media móvil normalizada en z (reflejo en bordes)
W = 41
ker = np.ones(W, np.float32)
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

# --- 5) relleno de huecos pequeños en z (solo visual; grandes → blanco)
idx = np.arange(nz)
Dv = np.full_like(D, np.nan)
for a in range(nk):
    for i in range(60):
        col = D[a, i]; ok = np.isfinite(col)
        if ok.sum() < 2:
            Dv[a, i] = col
            continue
        pos = idx[ok]
        lleno = np.interp(idx, pos, col[ok])
        j = np.searchsorted(pos, idx)
        j0 = np.clip(j - 1, 0, len(pos) - 1)
        j1 = np.clip(j, 0, len(pos) - 1)
        dist = np.minimum(np.abs(idx - pos[j0]), np.abs(idx - pos[j1]))
        Dv[a, i] = np.where(dist <= GAP_Z, lleno, np.nan)

# --- 6) desarrollo real y pintado por promedio (paso 0,5 mm)
rv = rmed.ravel()
drv = np.diff(rv, prepend=rv[0])
seg = np.sqrt((rv * np.radians(6.0)) ** 2 + drv ** 2)
Lfin = np.cumsum(seg); Lini = Lfin - seg; Lmax = Lfin[-1]
paso = 0.5
ncol = int(np.ceil(Lmax / paso))
ACC = np.zeros((nz, ncol), np.float32)
CNT = np.zeros((nz, ncol), np.float32)
cobL = np.zeros(ncol, np.float32)                  # cobertura real por columna
for a in range(nk):
    for i in range(60):
        j = a * 60 + i
        c0 = int(Lini[j] / paso)
        c1 = min(max(c0 + 1, int(np.ceil(Lfin[j] / paso))), ncol)
        if c1 <= c0:
            continue
        cobL[c0:c1] = np.maximum(cobL[c0:c1],
                                 np.isfinite(D[a, i]).mean())
        col = Dv[a, i]; fn = np.isfinite(col)
        if not fn.any():
            continue
        ACC[fn, c0:c1] += col[fn, None]
        CNT[fn, c0:c1] += 1
IMG = np.divide(ACC, CNT, out=np.full_like(ACC, np.nan), where=CNT > 0)
bordes = Lfin[59::60] / 1000

# --- 7) figura principal: cinta + banda de cobertura
v = np.nanpercentile(np.abs(IMG), 95)
fig = plt.figure(figsize=(22, 5.6))
gs = gridspec.GridSpec(2, 1, height_ratios=[9, 1.3], hspace=0.06)
ax = fig.add_subplot(gs[0])
im = ax.imshow(IMG, aspect="auto", origin="lower", cmap="RdBu_r",
               vmin=-v, vmax=v, extent=[0, Lmax / 1000, 0, nz * dz_mm])
for b in bordes[:-1]:
    ax.axvline(b, color="k", lw=0.3, alpha=0.35)
fig.colorbar(im, ax=ax, label="relieve radial (mm)", pad=0.01)
ax.set_ylabel("altura (mm)")
ax.set_xticklabels([])
ax.set_title(f"PHerc1218 — el pergamino desplegado: {Lmax/1000:.1f} m "
             f"de cinta continua ({nk} vueltas con datos), "
             "relieve del aplastamiento")
ax2 = fig.add_subplot(gs[1], sharex=ax)
Lx = (np.arange(ncol) + 0.5) * paso / 1000
ax2.fill_between(Lx, 0, 100 * cobL, color="0.35", lw=0)
ax2.set_ylim(0, 100); ax2.set_xlim(0, Lmax / 1000)
ax2.set_ylabel("dato\n(%)", fontsize=8)
ax2.set_xlabel("desarrollo del papiro (m) — del núcleo hacia fuera "
               "(rayas finas: cambio de vuelta; longitudes por geometría "
               "mediana, variación real por altura de unos %)")
plt.savefig("pergamino_desplegado_1218.png", dpi=150, bbox_inches="tight")
plt.show()

# --- 8) figura de diagnóstico: dónde muere la segmentación (vuelta × θ)
plt.figure(figsize=(14, 3.6))
plt.imshow(100 * cob2d.T, aspect="auto", origin="lower", cmap="viridis",
           vmin=0, vmax=100,
           extent=[K0 - 0.5, K1 + 0.5, 0, 360])
plt.colorbar(label="cobertura (%)", pad=0.01)
plt.xlabel("vuelta k (del núcleo hacia fuera)")
plt.ylabel("θ (°)")
plt.title("PHerc1218 — censo de la segmentación: cobertura por (vuelta, θ) "
          "— ¿muere uniforme o por un flanco?")
plt.tight_layout()
plt.savefig("cobertura_1218.png", dpi=150, bbox_inches="tight")
plt.show()

cobS = np.convolve(cobL, np.ones(40) / 40, "same")   # suavizada ~2 cm
L50 = Lx[cobS >= 0.5][-1] if (cobS >= 0.5).any() else 0
print(f"guardadas ambas figuras — cinta {Lmax/1000:.2f} m, "
      f"vueltas {K0}..{K1}, relieve típico ±{v:.2f} mm; "
      f"cobertura sostenida ≥50% hasta L = {L50:.2f} m")
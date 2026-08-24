# =====================================================================
# CELDA VOTE-2 — vuelta POR PUNTO vía el perfil radial del rayo,
#                y las instancias relegadas a QA (PHerc1218, Ruta B)
#
# LECCIÓN DE VOTE-1 (error de diseño, confesado): la instancia NO es la
# unidad de la vuelta. El rollo es UNA hoja en espiral: una instancia
# bien cosida DEBE cruzar muchas vueltas (la mayor recibió 176.859 votos
# de decenas de k — eso es topología, no fallo). La pureza era la métrica
# equivocada. Aquí la vuelta se asigna PUNTO A PUNTO: cada punto
# etiquetado se encaja entre los radios de la tabla en su propio rayo
# (θ,z), y la instancia queda para lo que sí sirve: cazar contradicciones
# físicas (misma instancia, mismo rayo y plano, dos vueltas distintas =
# candidato a costura/salto, el QA prometido a J).
#
# ORDEN tras (re)conexión: (1) celda de carga de la tabla → (2) esta.
# No necesita VOTE-1 ni TEX-0 ni el volumen CT.
#
# Salidas:
#   puntos_vuelta_1218.npz      (x,y,z,instancia,k,Δr por punto — semilla Ruta A)
#   qa_instancias_1218.csv      (contradicciones mismo-rayo por instancia)
#   vote2_diagnostico.png       (Δr y ambigüedad, antes del corte)
#   vote2_hoja_subsample.png    (la hoja plana por-vóxel, presencia)
#
# Criterios PREFIJADOS (antes de correr):
#   EXAMEN A2: ≥60% de puntos con asignación no ambigua
#   EXAMEN B2: mediana |Δr| de los asignados ≤ 3 vox
#   Contexto (sin veredicto): tasa de celdas-rayo contradictorias vs el
#   prior de costuras de J (~17% de vóxeles de costura con fallo de merge)
# =====================================================================
import numpy as np, pandas as pd, csv, io, os, glob, time, urllib.request
import matplotlib.pyplot as plt

t0 = time.time()
for v in ["rows", "zs", "zpos"]:
    assert v in dir(), f"falta {v}: corre primero la celda de carga de la tabla"

VOX      = 0.01728
TOL_ABS  = 15.0   # vox: cota dura de |Δr| (holgada; el grosor de hoja es 6-12)
TOL_FRAC = 0.45   # el punto debe estar a <45% del hueco local de su ganador
COB_MIN  = 0.10   # para el eje L de la figura (como DES-1)

# ---------- 1. orígenes (marco de etiquetas; offset (0,0) validado en VOTE-1)
RAW = ("https://raw.githubusercontent.com/Jinhojeong/"
       "vesuvius-surface-geometry-diagnostic/main/results/kollesis/")
texto = urllib.request.urlopen(RAW + "origins_merged.csv").read().decode()
acum = {}
for f_ in csv.DictReader(io.StringIO(texto)):
    z = int(float(f_["z"]))
    acum.setdefault(z, []).append((float(f_["cx"]), float(f_["cy"])))
origins = {z: (np.mean([p[0] for p in v]), np.mean([p[1] for p in v]))
           for z, v in acum.items()}
zso = sorted(origins)
for z in zs:
    if z not in origins:
        origins[z] = origins[min(zso, key=lambda q: abs(q - z))]

# ---------- 2. perfil radial de la tabla: Rg[k, rayo, plano] en vox ---------
kmax = max(int(r["k"]) for r in rows)
nzp = len(zs)
Rg = np.full((kmax + 1, 60, nzp), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]),
       int(round(float(r["theta_deg"]) / 6)) % 60,
       zpos[int(r["z"])]] = float(r["r_l1_vox"])
print(f"tabla: {len(rows):,} cruces | perfil Rg {Rg.shape}")

# ---------- 3. subsample de etiquetas (Kaggle, cacheado si ya se bajó) ------
try:
    import kagglehub
except ImportError:
    os.system("pip install -q kagglehub")
    import kagglehub
ruta = kagglehub.dataset_download("jhjeong0815/pherc1218-label-points")
cands = (glob.glob(ruta + "/**/*.parquet", recursive=True)
         + glob.glob(ruta + "/**/*.csv*", recursive=True))
fdat = max(cands, key=os.path.getsize)
df = (pd.read_parquet(fdat) if fdat.endswith(".parquet")
      else pd.read_csv(fdat))
df.columns = [c.strip().lower() for c in df.columns]
zset = set(int(z) for z in zs)
df = df[df["z"].isin(zset)].sort_values("z")
LX  = df["x"].to_numpy(np.float64)
LY  = df["y"].to_numpy(np.float64)
LZ  = df["z"].to_numpy(np.int32)
LID = df["instance_id"].to_numpy(np.int64)
lim = {z: (np.searchsorted(LZ, z, "left"), np.searchsorted(LZ, z, "right"))
       for z in zset}
print(f"etiquetas en los 323 planos de la tabla: {len(LZ):,}  "
      f"[{time.time()-t0:.0f}s]")

# ---------- 4. asignación por punto: encaje en el perfil del rayo -----------
KAS = np.full(len(LZ), -1, np.int16)     # vuelta asignada (-1 = sin asignar)
D1  = np.full(len(LZ), np.nan, np.float32)   # |Δr| al ganador
FRC = np.full(len(LZ), np.nan, np.float32)   # d1/(d1+d2): ambigüedad
IR  = np.zeros(len(LZ), np.int16)            # rayo (0..59)
for z in sorted(zset):
    a, b = lim[z]
    if a == b: continue
    iz = zpos[z]; ox, oy = origins[z]
    x = LX[a:b] - ox; y = LY[a:b] - oy
    th = np.degrees(np.arctan2(y, x)) % 360.0
    ir = (np.rint(th / 6.0).astype(np.int64)) % 60
    rp = np.hypot(x, y)
    M = Rg[:, ir, iz]                        # (nk+1, Np) radios del rayo
    D = np.abs(M - rp[None, :])
    D = np.where(np.isfinite(D), D, np.inf)
    j = np.arange(D.shape[1])
    k1 = np.argmin(D, axis=0)
    d1 = D[k1, j]
    D[k1, j] = np.inf
    d2 = np.min(D, axis=0)                   # segundo mejor (hueco local)
    frac = d1 / np.maximum(d1 + d2, 1e-9)
    KAS[a:b] = np.where(np.isfinite(d1), k1, -1).astype(np.int16)
    D1[a:b]  = np.where(np.isfinite(d1), d1, np.nan)
    FRC[a:b] = np.where(np.isfinite(frac), frac, np.nan)
    IR[a:b]  = ir.astype(np.int16)

fin = np.isfinite(D1)
print(f"\n|Δr| al ganador (ANTES de cortar): p50 {np.nanpercentile(D1,50):.1f}  "
      f"p90 {np.nanpercentile(D1,90):.1f}  p99 {np.nanpercentile(D1,99):.1f} vox")
print(f"ambigüedad d1/(d1+d2): p50 {np.nanpercentile(FRC,50):.2f}  "
      f"p90 {np.nanpercentile(FRC,90):.2f}")
ok = fin & (D1 <= TOL_ABS) & (FRC <= TOL_FRAC)
KAS[~ok] = -1
fa = ok.mean()
print(f"puntos asignados sin ambigüedad: {ok.sum():,} ({fa:.1%})")
print(f"EXAMEN A2 (asignación ≥60%): {'PASS' if fa >= 0.60 else 'FAIL'}")
med = np.nanmedian(D1[ok])
print(f"|Δr| mediana de los asignados: {med:.2f} vox "
      f"({med*VOX*1000:.0f} µm; grosor de hoja 6-12 vox)")
print(f"EXAMEN B2 (mediana ≤3 vox): {'PASS' if med <= 3.0 else 'REVIEW'}")

# ---------- 5. QA de instancias: SALTOS en la secuencia de vueltas ----------
# Una instancia legítima es un trozo de la espiral: sus vueltas asignadas
# forman una secuencia CONSECUTIVA (…,k,k+1,k+2,…). Un hueco de ≥2 vueltas
# con puntos a ambos lados (k=5 y k=9 sin 6-7-8 en ninguna parte) no puede
# ser la espiral: candidato a fallo de merge/costura. OJO declarado: un
# salto de hoja a la vuelta VECINA (hueco=1) es indistinguible de la
# continuación legítima con este test — eso queda para la pasada completa.
dfa = pd.DataFrame({"inst": LID[ok], "k": KAS[ok]})
def resumen(g):
    ks = np.sort(g.unique())
    if len(ks) == 1:
        return pd.Series({"n_k": 1, "kmin": ks[0], "kmax": ks[0],
                          "hueco": 0, "lado_min": 0})
    difs = np.diff(ks)
    j = int(np.argmax(difs))
    corte = ks[j]
    ntot = g.value_counts()
    lado_a = int(ntot[ntot.index <= corte].sum())
    lado_b = int(ntot[ntot.index > corte].sum())
    return pd.Series({"n_k": len(ks), "kmin": ks[0], "kmax": ks[-1],
                      "hueco": int(difs[j]) - 1,
                      "lado_min": min(lado_a, lado_b)})
npts = dfa.groupby("inst")["k"].size().rename("n_pts")
qa = dfa.groupby("inst")["k"].apply(resumen).unstack()
qa = qa.join(npts)
salto = qa[(qa["hueco"] >= 2) & (qa["lado_min"] >= 3)]
base = qa[qa["n_pts"] >= 6]
print(f"\ninstancias evaluadas (≥6 puntos): {len(base):,} | con SALTO de "
      f"vueltas (hueco ≥2, ≥3 puntos por lado): {len(salto):,} "
      f"({len(salto)/max(1,len(base)):.1%}) — prior de J: ~17% de vóxeles "
      f"de costura con fallo de merge (contexto, no criterio)")
salto.sort_values("n_pts", ascending=False).reset_index()\
     .to_csv("qa_instancias_1218.csv", index=False)

# ---------- 6. ficheros + figuras -------------------------------------------
np.savez_compressed("puntos_vuelta_1218.npz",
                    x=LX[ok].astype(np.float32), y=LY[ok].astype(np.float32),
                    z=LZ[ok], inst=LID[ok], k=KAS[ok], dr=D1[ok])
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].hist(D1[fin].clip(0, 40), bins=80); ax[0].axvline(TOL_ABS, color="r")
ax[0].set_title("|Δr| al ganador (vox), antes del corte")
ax[1].hist(FRC[fin], bins=60); ax[1].axvline(TOL_FRAC, color="r")
ax[1].set_title("ambigüedad d1/(d1+d2)")
plt.tight_layout(); plt.savefig("vote2_diagnostico.png", dpi=120)

# eje L como DES-1 (geometría mediana en mm) y hoja plana por-vóxel
cob = np.isfinite(Rg).reshape(kmax + 1, -1).mean(axis=1)
K0 = 2
K1 = max(k for k in range(kmax + 1) if cob[k] >= COB_MIN)
nk = K1 - K0 + 1
rmed = np.nanmedian(Rg[K0:K1 + 1] * VOX, axis=2)
rk = np.nanmedian(rmed, axis=1)
f = np.isfinite(rk)
rk = np.interp(np.arange(nk), np.arange(nk)[f], rk[f])
for a2 in range(nk):
    fila = rmed[a2]; fila[~np.isfinite(fila)] = rk[a2]
rv = rmed.ravel()
seg = np.sqrt((rv * np.radians(6.0)) ** 2 + np.diff(rv, prepend=rv[0]) ** 2)
Lc = np.cumsum(seg) - seg / 2
selL = ok & (KAS >= K0) & (KAS <= K1)
Lpts = Lc[(KAS[selL].astype(np.int64) - K0) * 60 + IR[selL]]
Zpts = np.array([zpos[int(z)] for z in LZ[selL]])
plt.figure(figsize=(14, 5))
plt.hist2d(Lpts / 1000.0, Zpts, bins=[600, nzp],
           norm=plt.matplotlib.colors.LogNorm())
plt.xlabel("L desarrollada (m)"); plt.ylabel("plano z")
plt.title(f"Hoja plana POR-VÓXEL (subsample paso 8): "
          f"{selL.sum():,} puntos etiquetados en su sitio")
plt.colorbar(label="puntos/bin (log)")
plt.tight_layout(); plt.savefig("vote2_hoja_subsample.png", dpi=130)
print(f"\nficheros escritos; total {time.time()-t0:.0f}s")
# =====================================================================
# CELDA VOTE-1 — asignación instancia→vuelta por VOTACIÓN (PHerc1218)
# Ruta B: subsample de etiquetas de J (Kaggle, retícula paso 8, pre-repair)
#
# ORDEN tras (re)conexión del Colab:
#   (1) celda de carga de la tabla (define rows, zs, zpos)
#   (2) esta celda        — NO necesita TEX-0 ni el volumen CT
#
# Salidas:
#   mapping_instancia_vuelta_1218.csv   (instancia → vuelta, votos, pureza)
#   conflictos_votacion_1218.csv        (candidatos a costura / salto de hoja)
#   votos_1218.npz                      (por-cruce, para el DES a resolución sub)
#   vote1_diagnostico.png               (distancias, votos, pureza)
#
# Criterios PREFIJADOS (antes de correr):
#   EXAMEN A (cobertura): ≥70% de cruces con punto etiquetado a ≤R_MAX
#   EXAMEN B (pureza):    mediana de pureza ≥0.90 en instancias con ≥20 votos
#   Contexto (sin veredicto): tasa de instancias multi-vuelta vs el prior de
#   costuras de J (17.1% de vóxeles de costura con fallo de merge).
# =====================================================================
import numpy as np, pandas as pd, csv, io, os, glob, time, urllib.request
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt

t0 = time.time()
for v in ["rows", "zs", "zpos"]:
    assert v in dir(), f"falta {v}: corre primero la celda de carga de la tabla"

VOX   = 0.01728
R_MAX = 10.0   # vox, EN EL PLANO; < 11.6 vox (paso 0.20 mm entre hojas):
               # un voto no puede alcanzar la hoja vecina a espaciado nominal.
               # OJO: en flancos muy comprimidos el espaciado local puede bajar
               # de 10 — un conflicto con dist alta puede ser radio nuestro,
               # no costura de J. Por eso el CSV de conflictos guarda dist.
MIN_VOTOS_CONFLICTO = 5

# ---------- 1. orígenes por rebanada (marco de ETIQUETAS: SIN offset CT) ----
# La retícula de J está "same grid and axes as the crossing table": los
# orígenes son centroides de la máscara de etiquetas → aquí DX=DY=0.
# El (−3,−1) era el offset hacia el volumen CT (DES-2), no hacia las etiquetas.
# Aun así, abajo se comprueban ambos offsets sobre una muestra y gana el mejor.
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

# ---------- 2. cruces → (x,y) en el marco de etiquetas ----------------------
K  = np.array([int(r["k"]) for r in rows], np.int32)
TH = np.array([float(r["theta_deg"]) for r in rows], np.float32)
ZC = np.array([int(r["z"]) for r in rows], np.int32)
RR = np.array([float(r["r_l1_vox"]) for r in rows], np.float32)
OX = np.array([origins[int(z)][0] for z in ZC], np.float64)
OY = np.array([origins[int(z)][1] for z in ZC], np.float64)
XC = OX + RR * np.cos(np.radians(TH))
YC = OY + RR * np.sin(np.radians(TH))
print(f"cruces: {len(K):,}  |  rebanadas: {len(np.unique(ZC))}")

# ---------- 3. subsample de etiquetas de J (Kaggle) -------------------------
try:
    import kagglehub
except ImportError:
    os.system("pip install -q kagglehub")
    import kagglehub
try:
    ruta = kagglehub.dataset_download("jhjeong0815/pherc1218-label-points")
except Exception as e:
    raise RuntimeError(
        "descarga de Kaggle fallida — si pide credenciales: sube tu "
        "kaggle.json a /root/.kaggle/ y reintenta") from e
cands = (glob.glob(ruta + "/**/*.parquet", recursive=True)
         + glob.glob(ruta + "/**/*.csv*", recursive=True)
         + glob.glob(ruta + "/**/*.feather", recursive=True))
assert cands, f"sin fichero de datos en {ruta}: {os.listdir(ruta)}"
fdat = max(cands, key=os.path.getsize)
print("fichero:", os.path.basename(fdat))
if fdat.endswith(".parquet"):
    df = pd.read_parquet(fdat)
elif fdat.endswith(".feather"):
    df = pd.read_feather(fdat)
else:
    df = pd.read_csv(fdat)
df.columns = [c.strip().lower() for c in df.columns]
assert {"x", "y", "z", "instance_id"} <= set(df.columns), df.columns.tolist()
print(f"etiquetas: {len(df):,} filas, {df['instance_id'].nunique():,} ids")

# retícula: residuos modales (paso 8 declarado; el offset puede no ser 0)
for c in ["x", "y", "z"]:
    md = np.bincount(df[c].to_numpy().astype(np.int64) % 8).argmax()
    print(f"  retícula {c}: residuo modal mod 8 = {md}")

# quedarnos solo con los planos z que tocan a la tabla
zplanes = np.unique(df["z"].to_numpy())
zcru    = np.unique(ZC)
zlab_de = {int(z): int(zplanes[np.argmin(np.abs(zplanes - z))]) for z in zcru}
dzs = np.array([abs(z - zl) for z, zl in zlab_de.items()])
print(f"plano de etiquetas más cercano: |dz| max {dzs.max()} vox "
      f"(0 = retículas alineadas en z)")
df = df[df["z"].isin(set(zlab_de.values()))].sort_values("z")
LZ  = df["z"].to_numpy(np.int32)
LX  = df["x"].to_numpy(np.float64)
LY  = df["y"].to_numpy(np.float64)
LID = df["instance_id"].to_numpy(np.int64)
lim = {z: (np.searchsorted(LZ, z, "left"), np.searchsorted(LZ, z, "right"))
       for z in set(zlab_de.values())}
print(f"etiquetas en los planos de la tabla: {len(LZ):,}  "
      f"[{time.time()-t0:.0f}s]")

# ---------- 4. autocomprobación de offset sobre una muestra -----------------
def mediana_dist(dx, dy, planos):
    ds = []
    for z in planos:
        zl = zlab_de[int(z)]; a, b = lim[zl]
        if a == b: continue
        sel = ZC == z
        tree = cKDTree(np.c_[LX[a:b], LY[a:b]])
        d, _ = tree.query(np.c_[XC[sel] + dx, YC[sel] + dy], k=1)
        ds.append(d)
    return np.median(np.concatenate(ds))
muestra = zcru[:: max(1, len(zcru) // 12)]
m00 = mediana_dist(0, 0, muestra)
m31 = mediana_dist(-3, -1, muestra)
print(f"  offset (0,0): mediana dist = {m00:.2f} vox")
print(f"  offset (-3,-1): mediana dist = {m31:.2f} vox")
DXv, DYv = (0, 0) if m00 <= m31 else (-3, -1)
print(f"offset elegido: ({DXv},{DYv})")

# ---------- 5. emparejado completo por planos -------------------------------
DIST = np.full(len(K), np.inf, np.float32)
IDN  = np.full(len(K), -1, np.int64)
for z in zcru:
    zl = zlab_de[int(z)]; a, b = lim[zl]
    if a == b: continue
    sel = np.where(ZC == z)[0]
    tree = cKDTree(np.c_[LX[a:b], LY[a:b]])
    d, ix = tree.query(np.c_[XC[sel] + DXv, YC[sel] + DYv], k=1)
    DIST[sel] = d
    IDN[sel]  = LID[a + ix]
fin = np.isfinite(DIST)
print(f"\ndistancias al vecino (todas, ANTES de cortar): "
      f"p50 {np.percentile(DIST[fin],50):.1f}  p90 {np.percentile(DIST[fin],90):.1f}  "
      f"p95 {np.percentile(DIST[fin],95):.1f}  p99 {np.percentile(DIST[fin],99):.1f} vox")
ok = fin & (DIST <= R_MAX)
frac = ok.mean()
print(f"cruces con voto (dist ≤ {R_MAX:.0f} vox): {ok.sum():,} ({frac:.1%})")
print(f"EXAMEN A (cobertura ≥70%): {'PASS' if frac >= 0.70 else 'FAIL'}")

# ---------- 6. votación instancia → vuelta ----------------------------------
dv = pd.DataFrame({"id": IDN[ok], "k": K[ok], "d": DIST[ok],
                   "x": XC[ok], "y": YC[ok], "z": ZC[ok]})
cnt = dv.groupby(["id", "k"]).size().rename("n").reset_index()
tot = cnt.groupby("id")["n"].sum().rename("votos")
top = (cnt.sort_values("n", ascending=False).groupby("id").first()
       .rename(columns={"k": "k_win", "n": "n_win"}))
mapa = top.join(tot)
mapa["pureza"] = mapa["n_win"] / mapa["votos"]
mapa["n_k"] = cnt.groupby("id")["k"].nunique()
print(f"\ninstancias con votos: {len(mapa):,} "
      f"(de {df['instance_id'].nunique():,} presentes en el subsample)")
print("votos por instancia: p50 {:.0f}  p90 {:.0f}  max {:,}".format(
    mapa["votos"].median(), mapa["votos"].quantile(.9), mapa["votos"].max()))
g20 = mapa[mapa["votos"] >= 20]
print(f"pureza (instancias ≥20 votos, n={len(g20):,}): "
      f"mediana {g20['pureza'].median():.3f}  p10 {g20['pureza'].quantile(.1):.3f}")
print(f"EXAMEN B (mediana pureza ≥0.90): "
      f"{'PASS' if g20['pureza'].median() >= 0.90 else 'REVIEW'}")
multi = mapa[(mapa["votos"] >= MIN_VOTOS_CONFLICTO) & (mapa["n_k"] > 1)]
base  = mapa[mapa["votos"] >= MIN_VOTOS_CONFLICTO]
print(f"instancias multi-vuelta (≥{MIN_VOTOS_CONFLICTO} votos): "
      f"{len(multi):,} de {len(base):,} ({len(multi)/max(1,len(base)):.1%}) — "
      f"prior de costuras de J: ~17% de vóxeles de costura con fallo de merge "
      f"(contexto, no criterio)")

# ---------- 7. ficheros -----------------------------------------------------
mapa.reset_index()[["id", "k_win", "votos", "n_win", "pureza", "n_k"]]\
    .to_csv("mapping_instancia_vuelta_1218.csv", index=False)
cnt2 = cnt.sort_values("n", ascending=False).copy()
cnt2["rk"] = cnt2.groupby("id").cumcount()
seg = (cnt2[cnt2["rk"] == 1].set_index("id")[["k", "n"]]
       .rename(columns={"k": "k_2", "n": "n_2"}))
conf = multi.join(seg, how="left")
cen = dv.groupby("id").agg(cx=("x", "median"), cy=("y", "median"),
                           cz=("z", "median"), d_med=("d", "median"))
conf = conf.join(cen)
conf.reset_index().to_csv("conflictos_votacion_1218.csv", index=False)
np.savez_compressed("votos_1218.npz",
                    k=K[ok], theta=TH[ok], z=ZC[ok], r=RR[ok],
                    x=XC[ok], y=YC[ok], inst=IDN[ok], dist=DIST[ok],
                    offset=np.array([DXv, DYv]))
fig, ax = plt.subplots(1, 3, figsize=(15, 4))
ax[0].hist(DIST[fin].clip(0, 30), bins=60); ax[0].axvline(R_MAX, color="r")
ax[0].set_title("dist al punto etiquetado (vox)")
ax[1].hist(np.log10(mapa["votos"]), bins=50)
ax[1].set_title("votos por instancia (log10)")
ax[2].hist(g20["pureza"], bins=40)
ax[2].set_title("pureza (instancias ≥20 votos)")
plt.tight_layout(); plt.savefig("vote1_diagnostico.png", dpi=120)
print(f"\nficheros escritos; total {time.time()-t0:.0f}s")
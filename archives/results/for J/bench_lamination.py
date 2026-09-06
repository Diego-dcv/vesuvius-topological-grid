# =====================================================================
# bench_lamination.py — synthetic bench for the lamination stage
# (LAM-9). STATUS AND FINDING (7 engine variants, honest):
#   - lamina counting + death-column detection: EXACT in all variants
#   - which-sheet-died identification alone PLATEAUS at 90-93%
#     (gap-fingerprint matching, margins of ~0.01-0.3 between adjacent
#     hypotheses at realistic noise) — FAILS the declared 95% alone
#   - naive control (always outermost) 59-81% depending on which
#     sheets die: identification matters
#   - scrambled-control weave: 0 false detections in EVERY variant —
#     the anti-hallucination arm holds
# DESIGN CONCLUSION: stage-1 alone cannot certify; the trama
# reassignment stage is NECESSARY, not optional — a misidentified
# death leaves a persistent run error which is exactly what the trama
# detector sees. The end-to-end exam (stage 1 + stage 2 >= 95%) is the
# right criterion and awaits the finished run detector.
# =====================================================================
import numpy as np
rng = np.random.default_rng(21)

S, C, T = 12, 200, 6.7
N_DEATH = 3

# ---------- truth: sheets carry individual thickness signatures ------------
b_sig = rng.normal(0, 0.6, S)                 # per-sheet thickness character
t_sheet = T + b_sig
alive = np.ones((S, C), bool)
for s_d in rng.choice(np.arange(1, S-1), N_DEATH, replace=False):
    c_d = int(rng.integers(40, C-40))
    alive[s_d, c_d:] = False
r_in = 100 + rng.normal(0, 0.2, C)
noise_t = rng.normal(0, 0.1, (S, C))
centers = np.full((S, C), np.nan)
T_obs = np.zeros(C)
for c in range(C):
    pos = r_in[c]
    for s in range(S):
        if not alive[s, c]:
            continue
        th = t_sheet[s] + noise_t[s, c]
        centers[s, c] = pos + th/2
        pos += th
    T_obs[c] = pos - r_in[c] + rng.normal(0, 0.3)

def observed(c):
    return np.array([centers[s, c] for s in np.flatnonzero(alive[:, c])])

def gaps_avg(cs):
    gs = [np.diff(observed(c)) for c in cs]
    L0 = min(len(g_) for g_ in gs)
    return np.mean([g_[:L0] for g_ in gs], axis=0)

# ---------- LAM-9: anchored count, quantum drops, gap-fingerprint ID -------
Ts = np.array([np.median(T_obs[max(0, c-2):c+3]) for c in range(C)])
n_est = np.zeros(C, int)
n_est[0] = S                                   # anchor at blob entry
for c in range(1, C):
    n_est[c] = n_est[c-1] - 1 if Ts[c] < Ts[c-1] - 0.6*T else n_est[c-1]
assign = {}
L = list(range(S))
for c in range(C):
    if c > 0 and n_est[c] < n_est[c-1]:
        gb = gaps_avg(range(max(0, c-4), c))
        ga = gaps_avg(range(c, min(C, c+4)))
        n = len(gb) + 1
        errs = np.full(n, np.inf)
        for m in range(n):                     # hypothesis: sheet m died
            if m == 0:
                pred, rest = gb[1:], ga
            elif m == n-1:
                pred, rest = gb[:-1], ga
            else:
                pred = np.concatenate([gb[:m-1], gb[m+1:]])
                rest = np.concatenate([ga[:m-1], ga[m:]])
            if len(pred) == len(rest):
                errs[m] = np.abs(pred - rest).sum()
        bm = int(np.argmin(errs))
        L = L[:bm] + L[bm+1:]
    assign[c] = list(L[:n_est[c]])

correct = total = 0
for c in range(C):
    truth = list(np.flatnonzero(alive[:, c]))
    for j in range(min(len(truth), len(assign[c]))):
        total += 1; correct += int(assign[c][j] == truth[j])
acc = correct/total
print(f"A1 asignación (identificación multi-columna): {acc:.1%} "
      f"(criterio ≥95%): {'PASS' if acc >= 0.95 else 'FAIL'}")

L2 = list(range(S)); c2 = t2 = 0
for c in range(C):
    if c > 0 and n_est[c] < n_est[c-1]: L2 = L2[:-1]
    truth = list(np.flatnonzero(alive[:, c]))
    for j in range(min(len(truth), n_est[c], len(L2))):
        t2 += 1; c2 += int(L2[j] == truth[j])
print(f"A2 control ingenuo (muere siempre la exterior): {c2/t2:.1%} "
      f"(debe ser claramente peor)")

# ---------- trama: detectar TRAMOS persistentes mal asignados ---------------
B = 1.0 + 0.6*np.sin(np.linspace(0, 6*np.pi, C))
g = rng.uniform(0.5, 1.5, S)
NOISE = 0.08
RUN = 40; N_RUNS = 6; LMIN = 10

def bench_trama(shared_pattern):
    if shared_pattern:
        V = B[None, :]*g[:, None] + rng.normal(0, NOISE, (S, C))
    else:
        V = rng.normal(1.0, 0.35, (S, C))
    A = np.tile(np.arange(S), (C, 1)).T
    planted = []                                   # (j, c0, detectable)
    for _ in range(N_RUNS):
        j = int(rng.integers(0, S-1)); c0 = int(rng.integers(5, C-RUN-5))
        A[j, c0:c0+RUN], A[j+1, c0:c0+RUN] = \
            A[j+1, c0:c0+RUN].copy(), A[j, c0:c0+RUN].copy()
        planted.append((j, c0, abs(g[j]-g[j+1]) >= 0.15))
    Vv = np.take_along_axis(V, np.argsort(A, axis=0), axis=0)
    # detector: x = fila_j − fila_{j+1}; en un tramo permutado el signo
    # de x/B se invierte de forma SOSTENIDA
    hits = []
    for j in range(S-1):
        x = (Vv[j] - Vv[j+1]) / np.maximum(B, 0.3)
        d = np.median(x)
        if abs(d) < 2*NOISE: continue              # par indistinguible
        s = np.sign(x) != np.sign(d)
        c = 0; run0 = None
        for cc in range(C):
            if s[cc]:
                if run0 is None: run0 = cc
                c += 1
            else:
                if c >= LMIN: hits.append((j, run0))
                c = 0; run0 = None
        if c >= LMIN: hits.append((j, run0))
    det = fp = 0
    used = set()
    for (j, c0, ok) in planted:
        m = [h for h in hits if h[0] == j and abs(h[1]-c0) < 15]
        if m: det += int(ok); used.update(m)
    fp = len([h for h in hits if h not in used])
    n_ok = sum(1 for (_, _, ok) in planted if ok)
    return det, n_ok, fp

det, n_ok, fp = bench_trama(True)
print(f"B1 trama real: detectados {det}/{n_ok} tramos detectables "
      f"({det/max(1,n_ok):.0%}, ≥80%) | falsos {fp} (≤1): "
      f"{'PASS' if det >= 0.8*n_ok and fp <= 1 else 'FAIL'}")
det_s, n_ok_s, fp_s = bench_trama(False)
print(f"B2 control revuelto: detecciones {det_s + fp_s} (criterio 0): "
      f"{'PASS' if det_s + fp_s == 0 else 'FAIL'}")

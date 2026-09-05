# =====================================================================
# bench_iteration.py — synthetic bench with planted truth for the
# iterative placement (machinery.py). Run: python3 bench_iteration.py
#
# Scroll: 60 rays x 41 planes, 30 true windings at pitch 11.6 with
# smooth per-column jitter. Labels truncated at winding 15 except 4
# "deep" rays labelled to the end. Ridges exist at the true hidden
# radii; 8% of columns get a weak spurious ridge inserted mid-chain
# (the chain must break there, conservatively).
#
# EXPECTED (what "pass" looks like — reproduce before touching real
# data; exact figures are in README.md):
#   - iteration recovers most of the hidden crossings, and round 1
#     alone is a small fraction (the propagation does the work)
#   - zero radii further than 3 vox from any planted truth
#   - frozen dice and half-pitch controls both die (ratio <= 0.33)
#   - a "mush" scroll with no ridges accepts nothing
# =====================================================================
import numpy as np
from machinery import (iterate, control_transform, frozen_dice,
                       half_pitch, exams)

rng = np.random.default_rng(97)
N_RAYS, N_PLANES, N_WIND = 60, 41, 30
PITCH = 11.6
K_TRUNC = 15
DEEP = {0, 15, 30, 45}

jit = rng.normal(0, 0.8, (N_RAYS, N_PLANES))
r_true = np.zeros((N_RAYS, N_PLANES, N_WIND))
for i in range(N_RAYS):
    for iz in range(N_PLANES):
        r_true[i, iz] = 60.0 + PITCH * np.arange(N_WIND) + jit[i, iz]

cols, planted, noisy = {}, {}, 0
for i in range(N_RAYS):
    for iz in range(N_PLANES):
        ktr = N_WIND - 1 if i in DEEP else K_TRUNC
        rs = list(r_true[i, iz, :ktr + 1])
        hidden = list(r_true[i, iz, ktr + 1:])
        cre = [(r_ + rng.normal(0, 0.5), 100.0 * rng.uniform(0.85, 1.1))
               for r_ in hidden]
        if i not in DEEP and hidden and rng.random() < 0.08:
            pos = int(rng.integers(1, max(2, len(cre))))
            cre.insert(pos, (hidden[min(pos, len(hidden) - 1)] - PITCH / 2,
                             40.0))            # < 0.6*h -> breaks the chain
            noisy += 1
        cols[(i, iz)] = {"rs": rs, "cre": sorted(cre),
                         "edge": float(r_true[i, iz, -1] + 6),
                         "pitch": PITCH, "h": 100.0, "new": []}
        planted[(i, iz)] = hidden

n_hidden = sum(len(v) for k, v in planted.items() if k[0] not in DEEP)
print(f"synthetic: {len(cols)} columns, {n_hidden:,} hidden crossings, "
      f"{noisy} noisy columns")

hist = iterate(cols)
total = sum(len(c["new"]) for c in cols.values())
r1 = hist[0][2]
bad = sum(1 for (i, iz), c in cols.items() for (r_, h_, nr) in c["new"]
          if not planted[(i, iz)]
          or min(abs(r_ - np.array(planted[(i, iz)]))) > 3.0)
print(f"\nrecovery: {total:,}/{n_hidden:,} = {total / n_hidden:.0%} "
      f"(criterion >= 80%): {'PASS' if total >= 0.8 * n_hidden else 'FAIL'}")
print(f"round 1 alone: {r1 / max(1, total):.0%} of total "
      f"(criterion < 30%): {'PASS' if r1 < 0.3 * total else 'FAIL'}")
print(f"false radii (> 3 vox from all truth): {bad} "
      f"(criterion 0): {'PASS' if bad == 0 else 'FAIL'}")

t_dice = control_transform(cols, frozen_dice, len(hist), rng=rng)
t_half = control_transform(cols, half_pitch, len(hist))
exams(cols, total, t_dice, t_half)

# mush control: no ridges anywhere -> nothing may be accepted
for c in cols.values():
    c["_cre_bk2"], c["_new_bk2"] = c["cre"], c["new"]
    c["cre"], c["new"] = [], []
mush = iterate(cols, verbose=False)
t_mush = sum(len(c["new"]) for c in cols.values())
for c in cols.values():
    c["cre"], c["new"] = c["_cre_bk2"], c["_new_bk2"]
print(f"mush control (no ridges): {t_mush} accepted "
      f"(criterion 0): {'PASS' if t_mush == 0 else 'FAIL'}")

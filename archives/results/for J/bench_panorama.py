# =====================================================================
# bench_panorama.py — the GLOBAL exam (planted truth): does adding the
# placements HEAL the vertical lines of the sheet, or break them?
# Run: python3 bench_panorama.py
#
# Rationale (Diego's): judging crumb by crumb is not enough — the
# whole picture obeys rules no single crumb can violate unseen. Sheets
# cannot cross or reorder; a wrong placement bends the panorama.
# Operationalised: trace ALL verticals by radius continuity (TIGHT
# tracker, tol 0.35 x local pitch — at 0.55 the exam had no power:
# half-pitch ghosts healed the lines too) over four fields:
#   base    : truncated labels, no placements  (broken lines)
#   real    : placements at the true positions (must heal)
#   incoh   : placements shifted +-pitch/2 with a random sign per
#             plane — the realistic error (must heal <= 1/3 of real)
#   coh     : everything shifted +pitch/2 coherently — DECLARED
#             UNDETECTABLE by internal geometry (a coherent shift is a
#             valid picture); only the external CT-vein arm catches it
#             (brightness on-position vs half-pitch off, in open zones)
# Health = solid (non-bridged) traced points.
# =====================================================================
import numpy as np

rng = np.random.default_rng(7)
NZ, NK, PITCH = 60, 20, 10.0
izc = NZ // 2
TOL = 0.35

wave = 1.5 * np.sin(np.linspace(0, 3 * np.pi, NZ))[:, None]
r_true = (50 + PITCH * np.arange(NK)[None, :] + wave
          + rng.normal(0, 0.4, (NZ, NK)))
trunc = rng.random(NZ) < 0.5

def field(mode):
    F = []
    for iz in range(NZ):
        base = list(r_true[iz, :12 if trunc[iz] else NK])
        extra = []
        if trunc[iz] and mode != "base":
            sh = {"real": 0.0, "coh": PITCH / 2,
                  "incoh": rng.choice([-1, 1]) * PITCH / 2}[mode]
            extra = [r_true[iz, k] + sh for k in range(12, NK)]
        F.append(np.array(sorted(base + extra)))
    return F

def trace_all(F):
    lines = []
    for r0 in F[izc]:
        solid = np.zeros(NZ, bool)
        for direction in (1, -1):
            r_prev, fails = r0, 0
            rng_iz = range(izc, NZ) if direction == 1 else range(izc, -1, -1)
            for iz in rng_iz:
                rads = F[iz]
                if not len(rads):
                    fails += 1
                    continue
                j = np.argmin(np.abs(rads - r_prev))
                steps = np.diff(rads)
                step = np.median(steps) if len(steps) else PITCH
                if abs(rads[j] - r_prev) <= TOL * step:
                    solid[iz] = True
                    r_prev = rads[j]
                    fails = 0
                else:
                    fails += 1
                    if fails > 30:
                        break
        lines.append(solid)
    return lines

def health(F):
    return sum(int(s.sum()) for s in trace_all(F))

s_base = health(field("base"))
s_real = health(field("real"))
s_inco = health(field("incoh"))
g_real, g_inco = s_real - s_base, s_inco - s_base
print(f"health (solid points): base {s_base} | +real {s_real} "
      f"(gain {g_real}) | +incoherent {s_inco} (gain {g_inco})")
ratio = g_inco / max(1, g_real)
print(f"HEALING: incoherent/real gain ratio {ratio:.2f} "
      f"(criterion <= 0.33, and real gain > 0): "
      f"{'PASS' if g_real > 0 and ratio <= 0.33 else 'FAIL'}")

# vein arm: synthetic brightness lit only at true sheet radii
def on_vein_fraction(shift):
    hit = tot = 0
    for iz in range(NZ):
        if not trunc[iz]:
            continue
        for k in range(12, NK):
            r_ = r_true[iz, k] + shift
            hit += int(np.min(np.abs(r_ - r_true[iz])) < 2.0)
            tot += 1
    return hit / max(1, tot)

f_real, f_coh = on_vein_fraction(0.0), on_vein_fraction(PITCH / 2)
print(f"VEIN: real on-vein {f_real:.0%} | coherent ghost {f_coh:.0%} "
      f"(criterion real - ghost >= 0.25): "
      f"{'PASS' if f_real - f_coh >= 0.25 else 'FAIL'}")
print("\nDECLARED: internal geometry catches the incoherent error; the "
      "coherent global shift is only caught by the vein arm.")

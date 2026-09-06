# =====================================================================
# machinery.py — the iterative placement locks and the two fair
# controls, as pure functions over a column dictionary.
# PHerc.1218 topological-grid project (Diego-dcv) — package for J.
#
# DATA STRUCTURE
#   cols : dict keyed by (ray_index, plane_index) -> {
#     "rs":    sorted list of labelled crossing radii (vox) — the known
#              sheets of this column (may include externally verified
#              seed positions),
#     "cre":   sorted list of (radius, height) candidate ridges beyond
#              the labelled frontier — brightness peaks in the raw CT
#              (find_peaks, prominence >= 15, on a 3-vox smoothed
#              radial profile),
#     "edge":  outermost radius of dense CT material on this ray (vox),
#     "pitch": local winding pitch (vox), clamped to [7, 25],
#     "h":     reference ridge height = median peak height over the
#              labelled span of this column,
#     "new":   accepted placements, list of (radius, height, round_no) }
#   On a per-voxel tree, "rays" become whatever angular sampling the
#   tree provides; neighbours are the adjacent columns in angle and z.
#
# LOCKS (a candidate must pass all three)
#   1. spacing chain: distance from the current frontier (labelled max
#      + previously accepted) within [0.5, 2.5] x local pitch; the
#      chain BREAKS at the first violation (everything beyond is
#      dropped, conservative).
#   2. height: ridge height >= 0.6 x column reference h.
#   3. continuity (ordinal-free): some neighbouring column (ray +-1 or
#      plane +-1) has a crossing beyond MY labelled frontier within
#      |dr| <= DR_VEC after compensating the local radial drift
#      between the two columns (median offset of my last 3 labelled
#      sheets to their nearest counterparts in the neighbour).
#      DR_VEC must be < pitch/2 or the lock is vacuous: with +-7 vox
#      windows at 11.6 pitch the windows tile the whole range (our
#      first, failed version — kept here as a warning).
#
# FAIR CONTROLS (run through the SAME iteration, same number of
# rounds; the biased dice control that re-rolls every round and grants
# perfect heights is NOT fair — it failed both directions for us)
#   frozen_dice(col): random radii drawn ONCE per column, uniform over
#     (frontier+3, max(edge, ridges)), PAIRED with the real ridge
#     heights. Kills: positional luck.
#   half_pitch(col):  the same real ridges shifted +pitch/2 — no dice.
#     Positions that cannot be papyrus-on-its-sheet. Kills: any lock
#     that does not truly measure sheet alignment.
# PRE-DECLARED CRITERION: accepted(control)/accepted(real) <= 0.33 for
# BOTH controls, or nothing is exported.
#
# OUR RESULTS AT 6-DEGREE SAMPLING (60 rays), for reference:
#   synthetic bench (planted truth): real recovery 96%, frozen dice
#   ratio 0.02, half-pitch 0.00  -> the controls are not soft.
#   real scroll: frozen dice 0.80, half-pitch 1.19 -> FAIL, nothing
#   exported; measured cause: sheet radius decorrelates by more than
#   pitch/2 (~86 um) between rays 6 degrees apart.
# =====================================================================
import numpy as np

DR_VEC = 4.0          # vox; must stay < pitch/2 (see LOCKS note)
MAX_ROUNDS = 10
MIN_NEW_PER_ROUND = 20
E4_RATIO_MAX = 0.33
E3_PITCH_RANGE = (8.7, 14.5)   # vox, labelled pitch +-25% (adapt per dataset)
COLLISION_FRAC = 0.4           # of local pitch, within-column exclusion


def one_round(cols, n_rays=60, dr_vec=DR_VEC):
    """One iteration round. Returns (accepted, n_candidates).
    accepted: list of (ray, plane, radius, height)."""
    cand = []
    for (i, iz), c in cols.items():
        frontier = max(c["rs"] + [x[0] for x in c["new"]])
        r_prev = frontier
        ridges = sorted([x for x in c["cre"] if x[0] > frontier + 3])
        for r_, h_ in ridges:                      # locks 1 and 2
            s_ = r_ - r_prev
            if not (0.5 * c["pitch"] <= s_ <= 2.5 * c["pitch"]):
                break
            if h_ < 0.6 * c["h"]:
                break
            cand.append((i, iz, r_, h_))
            r_prev = r_
    acc = []
    for (i, iz, r_, h_) in cand:                   # lock 3
        c = cols[(i, iz)]
        my_frontier = max(c["rs"])
        ok = False
        for di, dz in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            cv = cols.get(((i + di) % n_rays, iz + dz))
            if cv is None:
                continue
            drift = float(np.median(
                [min(cv["rs"], key=lambda q: abs(q - rm)) - rm
                 for rm in c["rs"][-3:]]))
            if abs(drift) > 1.5 * c["pitch"]:
                drift = 0.0
            for rv in cv["rs"] + [x[0] for x in cv["new"]]:
                if rv > my_frontier - 3 and abs(rv - (r_ + drift)) <= dr_vec:
                    ok = True
                    break
            if ok:
                break
        if ok:
            acc.append((i, iz, r_, h_))
    return acc, len(cand)


def filter_collisions(cols, acc):
    """E5: drop accepted candidates closer than COLLISION_FRAC x pitch
    to anything already in their column. Returns (kept, n_collisions).
    If collisions exceed max(20, 5% of candidates) in a round, STOP the
    iteration — that is the error-cascade signal."""
    kept, colls = [], 0
    for (i, iz, r_, h_) in acc:
        c = cols[(i, iz)]
        everything = c["rs"] + [x[0] for x in c["new"]]
        if any(abs(r_ - x) < COLLISION_FRAC * c["pitch"] for x in everything):
            colls += 1
        else:
            kept.append((i, iz, r_, h_))
    return kept, colls


def iterate(cols, n_rays=60, max_rounds=MAX_ROUNDS, verbose=True):
    """Run the full iteration. Mutates cols[...]["new"].
    Returns history [(round, n_candidates, n_accepted, n_collisions)]."""
    hist = []
    for nr in range(max_rounds):
        acc, ncand = one_round(cols, n_rays)
        acc, colls = filter_collisions(cols, acc)
        for (i, iz, r_, h_) in acc:
            cols[(i, iz)]["new"].append((r_, h_, nr))
        hist.append((nr, ncand, len(acc), colls))
        if verbose:
            print(f"round {nr}: candidates {ncand:,} -> "
                  f"accepted {len(acc):,} (collisions {colls})")
        if ncand > 0 and colls > max(20, 0.05 * ncand):
            print("E5 HALT: collision cascade — stop, keep prior rounds")
            break
        if len(acc) < MIN_NEW_PER_ROUND:
            break
    return hist


def control_transform(cols, transform, n_rounds, n_rays=60, rng=None):
    """Run the SAME iteration with each column's ridges replaced by
    transform(col) (a fair control). Restores state afterwards.
    Returns total accepted by the control."""
    for c in cols.values():
        c["_cre_bk"], c["_new_bk"] = c["cre"], c["new"]
        c["new"] = []
        c["cre"] = transform(c, rng) if rng is not None else transform(c)
    total = 0
    for nr in range(n_rounds):
        acc, _ = one_round(cols, n_rays)
        acc, _ = filter_collisions(cols, acc)
        for (i, iz, r_, h_) in acc:
            cols[(i, iz)]["new"].append((r_, h_, nr))
        total += len(acc)
    for c in cols.values():
        c["cre"], c["new"] = c["_cre_bk"], c["_new_bk"]
        del c["_cre_bk"], c["_new_bk"]
    return total


def frozen_dice(c, rng):
    """Fair control 1: random radii drawn once, real ridge heights."""
    front0 = max(c["rs"])
    beyond = sorted([x for x in c["cre"] if x[0] > front0 + 3])
    if not beyond:
        return []
    lo = front0 + 3
    hi = max([c["edge"]] + [x[0] for x in beyond])
    if hi <= lo + 1:
        return []
    rr = np.sort(rng.uniform(lo, hi, len(beyond)))
    return sorted((float(rr[j]), beyond[j][1]) for j in range(len(beyond)))


def half_pitch(c):
    """Fair control 2: the same real ridges shifted by pitch/2."""
    return sorted((r_ + c["pitch"] / 2.0, h_) for (r_, h_) in c["cre"])


def exams(cols, total_real, total_dice, total_shift):
    """Final pre-declared verdicts. Prints and returns overall pass."""
    r1 = total_dice / max(1, total_real)
    r2 = total_shift / max(1, total_real)
    steps = []
    for c in cols.values():
        rr = sorted(x[0] for x in c["new"])
        if len(rr) >= 2:
            steps.extend(np.diff(rr))
    p = float(np.median(steps)) if steps else float("nan")
    e3 = E3_PITCH_RANGE[0] <= p <= E3_PITCH_RANGE[1]
    print(f"E3 median accepted pitch: {p:.1f} "
          f"({'PASS' if e3 else 'FAIL'})")
    print(f"frozen dice ratio {r1:.2f}, half-pitch ratio {r2:.2f} "
          f"(criterion <= {E4_RATIO_MAX} for BOTH)")
    ok = e3 and r1 <= E4_RATIO_MAX and r2 <= E4_RATIO_MAX
    print("VERDICT:", "PASS — exportable" if ok
          else "FAIL — export nothing")
    return ok

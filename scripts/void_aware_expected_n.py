#!/usr/bin/env python3
"""
void_aware_expected_n.py — Void-aware expected winding count for layer-count QA.
Reference formulation + implementation + acceptance test.

Diego C. V. (vesuvius-topological-grid) — built against the pitch_qa_cells.csv
conventions published by iyando (vesuvius-sheet-tools): L1 grid 17.28 µm/vox,
theta in 6° bins measured CCW from +x at the slice centroid, pitch/span in
physical µm.

PROBLEM
-------
The naive expected count per (z, θ) cell,

    E_naive[N] = span/pitch + 1,

assumes compact winding: papyrus occupying the full radial span. On crushed
scrolls this is false — on stitched PHerc1218 the data imply ~63% of the median
radial span is unoccupied (voids), which inflates E_naive and drives
counted/expected to ~0.37 even where counting is fine. The ratio then measures
"how crushed is the scroll" instead of "how good is the labeling".

FORMULATION (void-aware)
------------------------
Input per ray: the ordered crossing positions r_1 < ... < r_k along the ray
(already computed upstream — the aggregates keep only k, median gap, span).

1. Reference pitch p_ref: median of gaps g_i = r_{i+1} - r_i restricted to the
   "plausible winding" band g_i ∈ [0.5, 2] × (global median gap) — robust to
   both fragmentation (tiny gaps) and voids (huge gaps).

2. Gap classification, with v_merge = 2.5 and v_void = 4 (defaults; sensitivity
   should be reported):
     g < 0.5 · p_ref          → FRAGMENT boundary (one wrap split in two)
     0.5–2.5 · p_ref          → normal winding gap (possibly containing merges)
     2.5–4 · p_ref            → ambiguous (merge run or small void) — counted
                                 as merge-expected but flagged
     g > 4 · p_ref            → VOID (papyrus absent; expected crossings: 0)

3. Void-aware expected count. Each gap "explains" the crossing on its far
   side, so:
     E_va[N] = 1 + Σ_gaps  f(g)/p_ref,
       f(g) = g      for normal, ambiguous AND fragment gaps
                      (a fragment's tiny gap adds ~0.15 expected — the extra
                       crossing is not an expected wrap, which is the point)
       f(g) = p_ref  for void gaps: the far-side wrap exists (1 expected),
                      the empty interior contributes nothing.
   Known limitation: a run of ≥3 consecutive merged wraps produces a gap that
   lands in the void class and is under-expected — heavy merge runs are
   indistinguishable from voids from positions alone; v_void is the knob and
   intensity data the disambiguator.

   In clean compact cells E_va ≈ counted by construction, so the ratio
   counted/E_va sits at 1 and its deviations isolate labeling pathology:
     ratio > 1  → fragmentation excess     ratio < 1 → merge excess.

4. Reported per cell: counted, E_naive, E_va, ratio_naive, ratio_va,
   void_fraction (Σ void gaps / span), n_fragment, n_ambiguous.

AGGREGATE FALLBACK (positions unavailable)
------------------------------------------
From (n_distinct, pitch_um, span_um) alone the void fraction cannot be
classified, only bounded: assuming no fragmentation/merges,
    void_fraction ≥ 1 − (n_distinct − 1) · pitch / span   (clamped to [0,1]).
This bound is what `--csv` mode reports; it is a floor, not an estimate.

ACCEPTANCE TEST (run with no arguments)
---------------------------------------
Synthetic rays with known pitch; inject each pathology and verify the estimator
separates them where the naive ratio cannot:
  clean            → ratio_va ≈ 1            (and ratio_naive ≈ 1)
  30% void span    → ratio_naive collapses,   ratio_va stays ≈ 1
  20% merges       → ratio_va < 0.9,          void_fraction ≈ 0
  20% fragmentation→ ratio_va > 1.1
  voids + merges   → ratio_va still < 0.9  (merge detection survives voids)

Usage:
  python void_aware_expected_n.py                 # acceptance test
  python void_aware_expected_n.py --csv pitch_qa_cells.csv   # aggregate bound demo
"""
import argparse
import csv as _csv
import sys

import numpy as np


# ------------------------------ core ---------------------------------------
def void_aware_expected(positions, v_merge=2.5, v_void=4.0):
    """positions: 1D array of crossing positions along one ray (any length unit).
    Returns dict with counted, expected_naive, expected_va, ratios, void_fraction,
    n_fragment, n_ambiguous. None if fewer than 3 crossings."""
    r = np.unique(np.asarray(positions, dtype=float))   # sort + dedupe:
    # duplicate positions (rounded centroids) drive the gap median to 0 and
    # p_ref to 0 -> ZeroDivisionError. Field-reported by iyando on the full
    # PHerc1218 run; dedupe here makes the function safe regardless of input.
    if r.size < 3:
        return None
    gaps = np.diff(r)
    med = np.median(gaps)
    if not np.isfinite(med) or med <= 0:
        return None
    band = gaps[(gaps >= 0.5 * med) & (gaps <= 2.0 * med)]
    p_ref = float(np.median(band)) if band.size else float(med)
    span = float(r[-1] - r[0])

    frag = gaps < 0.5 * p_ref
    void = gaps > v_void * p_ref
    ambig = (gaps > v_merge * p_ref) & ~void
    normal = ~(frag | void)

    f = np.where(void, p_ref, gaps)
    e_va = 1.0 + float(f.sum()) / p_ref
    e_naive = span / p_ref + 1.0
    counted = float(r.size)
    return {
        "counted": counted,
        "pitch_ref": p_ref,
        "expected_naive": e_naive,
        "expected_va": e_va,
        "ratio_naive": counted / e_naive,
        "ratio_va": counted / e_va,
        "void_fraction": float(gaps[void].sum()) / span if span > 0 else 0.0,
        "n_fragment": int(frag.sum()),
        "n_ambiguous": int(ambig.sum()),
    }


def aggregate_void_bound(n_distinct, pitch, span):
    """Floor on void fraction from aggregates alone (no frag/merge assumed)."""
    if not np.isfinite(n_distinct * pitch * span) or span <= 0:
        return np.nan
    return float(np.clip(1.0 - (n_distinct - 1.0) * pitch / span, 0.0, 1.0))


# -------------------------- acceptance test ---------------------------------
def _make_ray(rng, n_wraps=40, pitch=173.0, jitter=0.12):
    g = pitch * (1 + jitter * rng.standard_normal(n_wraps - 1))
    return np.concatenate([[0.0], np.cumsum(np.clip(g, pitch * 0.4, None))])


def _inject_voids(r, rng, frac=0.30):
    """Insert void stretches so ~frac of final span is empty."""
    r = r.copy()
    n_voids = 3
    total_void = frac / (1 - frac) * (r[-1] - r[0])
    for _ in range(n_voids):
        i = rng.integers(5, len(r) - 5)
        r[i:] += total_void / n_voids
    return r


def _inject_merges(r, rng, frac=0.20):
    keep = np.ones(len(r), bool)
    idx = rng.choice(np.arange(2, len(r) - 2), size=int(frac * len(r)), replace=False)
    keep[idx] = False
    return r[keep]


def _inject_frags(r, rng, frac=0.20):
    extra = [x + 0.15 * 173 * (1 + 0.3 * rng.standard_normal())
             for x in rng.choice(r[1:-1], size=int(frac * len(r)), replace=False)]
    return np.sort(np.concatenate([r, extra]))


def acceptance_test(seed=0):
    rng = np.random.default_rng(seed)
    cases, ok = [], True

    def run(name, r, want):
        nonlocal ok
        out = void_aware_expected(r)
        passed = want(out)
        ok &= passed
        cases.append((name, out, passed))

    base = _make_ray(rng)
    run("clean", base, lambda o: 0.93 <= o["ratio_va"] <= 1.07)
    run("30% voids", _inject_voids(base, rng),
        lambda o: 0.93 <= o["ratio_va"] <= 1.07 and o["ratio_naive"] < 0.8
        and o["void_fraction"] > 0.15)
    run("20% merges", _inject_merges(base, rng),
        lambda o: o["ratio_va"] < 0.92 and o["void_fraction"] < 0.05)
    run("20% frags", _inject_frags(base, rng),
        lambda o: o["ratio_va"] > 1.08)
    run("voids+merges", _inject_merges(_inject_voids(base, rng), rng),
        lambda o: o["ratio_va"] < 0.92 and o["void_fraction"] > 0.15)

    print(f"{'case':<14} {'ratio_naive':>12} {'ratio_va':>9} {'void_frac':>10} {'pass':>6}")
    for name, o, p in cases:
        print(f"{name:<14} {o['ratio_naive']:12.3f} {o['ratio_va']:9.3f} "
              f"{o['void_fraction']:10.3f} {'PASS' if p else 'FAIL':>6}")
    print(f"\nACCEPTANCE TEST: {'PASSED' if ok else 'FAILED'}")
    return 0 if ok else 1


# ----------------------------- CSV demo -------------------------------------
def csv_demo(path):
    rows = list(_csv.DictReader(open(path)))
    n = np.array([float(r["n_distinct"] or "nan") for r in rows])
    pitch = np.array([float(r["pitch_um"] or "nan") for r in rows])
    span = np.array([float(r["span_um"] or "nan") for r in rows])
    coe = np.array([float(r["counted_over_expected"] or "nan") for r in rows])
    bound = np.array([aggregate_void_bound(a, b, c) for a, b, c in zip(n, pitch, span)])
    m = np.isfinite(bound) & np.isfinite(coe)
    print(f"{m.sum()} usable cells of {len(rows)}")
    print(f"naive counted/expected: median {np.nanmedian(coe[m]):.2f}")
    print(f"void-fraction FLOOR (aggregates only): median {np.nanmedian(bound[m]):.2f}, "
          f"IQR {np.nanpercentile(bound[m],25):.2f}-{np.nanpercentile(bound[m],75):.2f}")
    print("\nInterpretation: with ~this much of the span void, E_naive is inflated by")
    print("1/(1-void_frac); correcting only the median floor already moves the global")
    print("ratio from ~0.37 toward ~1 — the remaining gap is what positions will resolve")
    print("into fragmentation vs merges per cell. The positions are the missing input.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="pitch_qa_cells.csv for the aggregate-bound demo")
    a = ap.parse_args()
    if a.csv:
        csv_demo(a.csv)
        return 0
    return acceptance_test()


if __name__ == "__main__":
    sys.exit(main())

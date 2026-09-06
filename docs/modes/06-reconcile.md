# 6 — Reconcile (`scripts/void_aware_expected_n.py`)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


Layer-count QA compares how many windings a ray crosses against how many it
*should* cross. The naive expectation, `span/pitch + 1`, assumes compact
winding — false on a crushed scroll, where internal voids inflate the span and
drive the ratio far below 1 for reasons that have nothing to do with labeling
quality.

This reformulates the expectation so that voids contribute nothing: each gap
explains the crossing on its far side, so a void contributes exactly one
expected winding (its far boundary) and nothing for the empty interior. In
short: **don't count the air.** The residual then isolates labeling pathology —
below 1 means merge excess, above 1 means fragmentation.

```bash
python scripts/void_aware_expected_n.py                    # acceptance test
python scripts/void_aware_expected_n.py --csv cells.csv    # aggregate-bound demo
```

**Validation.** The acceptance test injects each pathology into synthetic rays
and checks the estimator separates them: with 30% injected voids the naive
ratio collapses to 0.70 while the void-aware ratio holds at 1.00; merges read
below 1, fragmentation above 1, and merge detection survives voids.

**In production.** Run over the full PHerc1218 per-ray positions (1.46M
crossings, 21,070 cells) by another contributor, the acceptance test passed
unchanged on their machine before anything else ran. Two findings came out of
it: fragmentation-excess cells line up with slab boundaries — independently
re-detecting a labeling edge effect found by a different method — and merge
excess concentrates on the flattened axis of the scroll.

**Declared limits.** A run of ≥3 consecutive merged windings looks like a void
from positions alone; `v_void` is the knob, CT intensity the disambiguator.
Duplicate crossing positions (rounded centroids) are deduped inside the
function — a field report from the full-scroll run.

---


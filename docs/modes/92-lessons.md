# Lessons (kept on purpose)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


**The recurring failure has a shape.** Most errors recorded in this repository
were not wrong facts but wrong *comparisons*: two quantities that measure the
same thing in different conventions, compared as though they shared one. Exam A
of Mode 11 compared a function against its own inverse on the same grid. The
sheet was compared against a ground truth numbered from the opposite end. Each
slice was compared against a median of 313. Each looked like a substantive
result until the comparison was checked, and none was caught by inspecting the
answer — only by testing the instrument.

Our first line-spacing estimate (4.45 mm) was a resolution artifact: on a 13 mm strip
the FFT has only 3–4 usable bins in the whole 3–8 mm range, and the "peak" was bin
k = 3 of the strip height. Finding it, fixing it (cycle gating + spatial-domain
estimation) and reporting it is part of the method. Earlier script versions live in
`archives/`, each superseded by the integrated `scripts/grid_metric.py`.


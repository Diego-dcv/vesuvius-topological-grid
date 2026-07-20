#!/usr/bin/env python3
"""Negative control for grid_metric.py rank mode.

Generates candidates from one real surface: the original plus rotated, warped
and noisy copies. Acceptance test: `rank` must place the original FIRST with a
clear margin. Until it does, the rank mode is machinery, not a validated tool.
Usage: python make_rank_candidates.py SURFACE.png
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None

arr = np.array(Image.open(sys.argv[1]).convert('L'), dtype=np.float64)
rng = np.random.default_rng(0)
Image.fromarray(arr.astype(np.uint8)).save('cand_original.png')
Image.fromarray(ndimage.rotate(arr, 4.0, reshape=False, mode='reflect').astype(np.uint8)).save('cand_rotated.png')
h, w = arr.shape
yy, xx = np.mgrid[0:h, 0:w].astype(float)
# unwrap-error signature: LINES wobble vertically (1 mm amplitude, 30 mm wavelength)
warped = ndimage.map_coordinates(arr, [yy + 62*np.sin(2*np.pi*xx/1860), xx], mode='reflect')
Image.fromarray(warped.astype(np.uint8)).save('cand_warped.png')
noisy = np.clip(arr + rng.normal(0, 2.0*arr.std(), arr.shape), 0, 255)
Image.fromarray(noisy.astype(np.uint8)).save('cand_noisy.png')
print("candidates: cand_original / cand_rotated / cand_warped / cand_noisy")

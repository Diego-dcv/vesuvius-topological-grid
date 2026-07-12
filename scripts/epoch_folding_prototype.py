#!/usr/bin/env python3
"""
epoch_folding_prototype.py -- Plegado de epoca sobre lineas de texto (Paris 4).

Idea (importada de la astronomia de pulsares): la escritura es periodica; apilar
N instancias del patron (lineas de texto) promedia el ruido y gana señal ~sqrt(N).
El plegado DESTRUYE el texto (promedia lineas entre si): no sirve para leer,
sirve para DETECTAR presencia de tinta estructurada como escritura donde cada
letra individual esta bajo el ruido.

Objetivo real: intensidad CRUDA de superficies (no predicciones de modelos).
  - Sobre una prediccion ML limpia la ganancia es ~1 (nada que recuperar).
  - Sobre señal enterrada la ganancia crece con el ruido (validado: x2 a ruido 4x).

Uso previsto como tercer elemento del kit:
  1) la metrica de periodicidad MIDE la estructura,
  2) los mapas de divergencia ARBITRAN entre modelos,
  3) el plegado DETECTA tinta bajo el ruido sin ML.

Limite honesto de este prototipo: los centros de linea se detectan sobre la
imagen limpia (idealizado). Sobre datos crudos reales el algoritmo debe buscar
el periodo y la fase del plegado maximizando el contraste del perfil plegado
(busqueda periodo-fase, como en pulsares), no asumirlos conocidos. Esa busqueda
es el siguiente paso natural.

Requisitos: numpy, scipy, matplotlib, pillow.
Uso: python epoch_folding_prototype.py --input superficie.png --width-mm 129
"""
import argparse
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
Image.MAX_IMAGE_PIXELS = None


def line_centers(win, pixel_mm, p_min=2.0, p_max=8.0):
    prof = win.sum(axis=1)
    base = gaussian_filter1d(prof, sigma=max(3, int(p_max / pixel_mm)))
    p2 = gaussian_filter1d(prof - base, sigma=max(1, int(0.25 / pixel_mm)))
    peaks, _ = find_peaks(p2, distance=int(p_min / pixel_mm), prominence=p2.std() * 0.4)
    return peaks


def fold_lines(img, pixel_mm, win_w_mm=20.0, step_mm=12.0, half_mm=2.2,
               centers_from=None):
    """Apila perfiles verticales centrados en cada linea detectada.
    centers_from: imagen limpia opcional para detectar centros (validacion);
    por defecto se detectan sobre la propia imagen."""
    ref = img if centers_from is None else centers_from
    W = img.shape[1]
    win_w = int(win_w_mm / pixel_mm)
    step = int(step_mm / pixel_mm)
    half = int(half_mm / pixel_mm)
    strips = []
    for x0 in range(0, W - win_w, step):
        for pk in line_centers(ref[:, x0:x0 + win_w], pixel_mm):
            if pk - half >= 0 and pk + half < img.shape[0]:
                strips.append(img[pk - half:pk + half, x0:x0 + win_w].mean(axis=1))
    if len(strips) < 2:
        return None, []
    return np.mean(strips, axis=0), strips


def profile_snr(prof):
    return (prof.max() - prof.min()) / (np.std(np.diff(prof)) + 1e-12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--width-mm", type=float, required=True,
                    help="anchura fisica de la imagen en mm (calibra el pixel)")
    ap.add_argument("--noise-test", action="store_true",
                    help="validacion: entierra la imagen bajo ruido y mide la ganancia")
    args = ap.parse_args()

    arr = np.array(Image.open(args.input).convert("L"), dtype=np.float32) / 255.0
    pixel_mm = args.width_mm / arr.shape[1]
    print(f"pixel = {pixel_mm*1000:.1f} um")

    folded, strips = fold_lines(arr, pixel_mm)
    if folded is None:
        raise SystemExit("no se detectaron suficientes lineas")
    print(f"N = {len(strips)} lineas | SNR individual medio = "
          f"{np.mean([profile_snr(s) for s in strips]):.1f} | SNR plegado = {profile_snr(folded):.1f}")

    if args.noise_test:
        rng = np.random.default_rng(0)
        for nl in (1.0, 2.0, 4.0, 8.0):
            noisy = arr + rng.normal(0, nl * arr.std(), arr.shape)
            f2, s2 = fold_lines(noisy, pixel_mm, centers_from=arr)
            gi = np.mean([profile_snr(s) for s in s2])
            print(f"  ruido {nl:>3.0f}x: individual {gi:6.2f} | plegado {profile_snr(f2):6.2f} "
                  f"| ganancia x{profile_snr(f2)/gi:.1f}")


if __name__ == "__main__":
    main()
